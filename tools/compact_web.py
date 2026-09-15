#!/usr/bin/env python3
"""Share identical PCK payloads without changing any resource path or content.

Only the standalone, unencrypted PCK v4 produced by our Godot export is supported.
Directory layout: Godot core/io/file_access_pack.cpp, PackedSourcePCK::try_open_pack.
This operates on exported files, never on the editor's .godot cache.
"""

import gzip
import hashlib
import json
from pathlib import Path
import re
import struct
import sys


def read_pack(data: bytes) -> tuple[bytes, list[tuple[bytes, bytes]]]:
    if len(data) < 112 or struct.unpack_from("<4sI", data) != (b"GDPC", 4):
        raise ValueError("Expected a standalone Godot PCK v4")
    flags, base, directory = struct.unpack_from("<IQQ", data, 20)
    if flags != 2 or base != 112 or not base <= directory <= len(data) - 4:
        raise ValueError("Unsupported PCK flags or offsets")
    count = struct.unpack_from("<I", data, directory)[0]
    position = directory + 4
    entries = []
    names = set()
    for _ in range(count):
        length = struct.unpack_from("<I", data, position)[0]
        position += 4
        name = data[position:position + length]
        position += length
        offset, size, digest, flags = struct.unpack_from("<QQ16sI", data, position)
        position += 36
        if not name or name in names or flags or base + offset + size > directory:
            raise ValueError("Invalid or unsupported PCK entry")
        names.add(name)
        payload = data[base + offset:base + offset + size]
        if hashlib.md5(payload).digest() != digest:
            raise ValueError(f"Corrupted PCK resource: {name!r}")
        entries.append((name, payload))
    return data[:base], entries


def compact(data: bytes) -> bytes:
    header, entries = read_pack(data)
    output = bytearray(header)
    directory = bytearray(struct.pack("<I", len(entries)))
    offsets = {}
    for name, payload in entries:
        # Bytes as keys compare the actual content, including on hash collisions.
        if payload not in offsets:
            output.extend(b"\0" * (-len(output) % 16))
            offsets[payload] = len(output) - len(header)
            output.extend(payload)
        directory.extend(struct.pack("<I", len(name)))
        directory.extend(name)
        directory.extend(struct.pack("<QQ16sI", offsets[payload], len(payload), hashlib.md5(payload).digest(), 0))
    output.extend(b"\0" * (-len(output) % 16))
    struct.pack_into("<Q", output, 32, len(output))
    output.extend(directory)
    result = bytes(output)
    if read_pack(result)[1] != entries:
        raise ValueError("Compaction changed a resource path or its contents")
    return result


def finish_export(folder: Path, report_path: Path) -> None:
    pack = folder / "index.pck"
    original = pack.read_bytes()
    result = compact(original)
    html_path = folder / "index.html"
    html = html_path.read_text()
    config_match = re.search(r"const GODOT_CONFIG = (\{[^\n]+\});", html)
    if config_match is None:
        raise ValueError("Cannot update Godot's loading progress: export HTML has changed")
    config = json.loads(config_match[1])
    config["fileSizes"]["index.pck"] = len(result)
    html = html[:config_match.start(1)] + json.dumps(config, separators=(",", ":")) + html[config_match.end(1):]
    temporary = pack.with_suffix(".pck.tmp")
    temporary.write_bytes(result)
    temporary.replace(pack)
    html_path.write_text(html)
    sizes = {
        path.name: {
            "raw_bytes": path.stat().st_size,
            "gzip_bytes": len(gzip.compress(path.read_bytes(), compresslevel=6, mtime=0)),
        }
        for path in sorted(folder.iterdir()) if path.is_file() and not path.name.startswith(".")
    }
    total = sum(size["gzip_bytes"] for size in sizes.values())
    # Doom is requested only after choosing the hidden performance test, outside the initial pack.
    deferred = {
        path.name: {"raw_bytes": path.stat().st_size,
                    "gzip_bytes": len(gzip.compress(path.read_bytes(), compresslevel=6, mtime=0))}
        for path in sorted((folder / "doom").glob("*"))
        if path.name in {"doom.js", "doom.wasm", "doom1.wad", "default.cfg", "host.html"}
    }
    report = {
        "pck_before_bytes": len(original), "pck_after_bytes": len(result),
        "duplicate_bytes_removed": len(original) - len(result),
        "gzip_level": 6, "gzip_total_bytes": total, "files": sizes,
        "doom_deferred_files": deferred,
        "doom_deferred_gzip_bytes": sum(size["gzip_bytes"] for size in deferred.values()),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"WEB_SIZE: PCK {len(original) / 2**20:.2f} -> {len(result) / 2**20:.2f} MiB; gzip total {total / 2**20:.2f} MiB")
    if total > 50 * 2**20:
        raise SystemExit("WEB_SIZE: exceeds the 50 MiB gzip initial download budget")


if __name__ == "__main__":
    finish_export(Path(sys.argv[1]), Path(sys.argv[2]))
