#!/usr/bin/env python3
"""The smaller export must retain resource lookups and the fixed Web lighting."""

import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from compact_web import compact, finish_export, read_pack
from prepare_web import prepare


def fixture() -> bytes:
    # Two resource paths with identical data, plus one distinct binary resource.
    data = bytearray(112)
    struct.pack_into("<4sIIIIIQ", data, 0, b"GDPC", 4, 4, 7, 2, 2, 112)
    directory = bytearray(struct.pack("<I", 3))
    for name, payload in [(b"wood_a.ctex", b"same pixels" * 100), (b"wood_b.ctex", b"same pixels" * 100), (b"scene.scn", b"\0different\xff")]:
        name += b"\0" * (-len(name) % 4)
        directory.extend(struct.pack("<I", len(name)) + name)
        directory.extend(struct.pack("<QQ16sI", len(data) - 112, len(payload), hashlib.md5(payload).digest(), 0))
        data.extend(payload)
    struct.pack_into("<Q", data, 32, len(data))
    return bytes(data + directory)


class WebExportTests(unittest.TestCase):
    def test_deduplication_preserves_every_path_and_byte(self):
        original = fixture()
        result = compact(original)
        self.assertLess(len(result), len(original) - 1000)
        self.assertEqual(read_pack(result)[1], read_pack(original)[1])
        self.assertEqual(compact(result), result)

    def test_corrupt_or_unrecognized_pack_is_not_rewritten(self):
        for offset in (4, 20, 112):
            data = bytearray(fixture())
            data[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                compact(bytes(data))

    def test_loader_progress_matches_the_compacted_download(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "index.pck").write_bytes(fixture())
            config = {"fileSizes": {"index.pck": 9999, "index.wasm": 123}, "args": ["keep-me"]}
            (root / "index.html").write_text("const GODOT_CONFIG = " + json.dumps(config) + ";")
            finish_export(root, root.parent / (root.name + "-sizes.json"))
            updated = json.loads((root / "index.html").read_text().split(" = ")[1][:-1])
            self.assertEqual(updated["fileSizes"]["index.pck"], (root / "index.pck").stat().st_size)
            self.assertEqual(updated["args"], ["keep-me"])
            self.assertEqual(updated["fileSizes"]["index.wasm"], 123)
            (root.parent / (root.name + "-sizes.json")).unlink()

    def test_unknown_loader_does_not_leave_an_inconsistent_export(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = fixture()
            (root / "index.pck").write_bytes(original)
            (root / "index.html").write_text("unrecognized export template")
            with self.assertRaises(ValueError):
                finish_export(root, root / "report.json")
            self.assertEqual((root / "index.pck").read_bytes(), original)

    def test_download_budget_rejects_even_an_overflow_hidden_by_rounding(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "web"
            root.mkdir()
            (root / "index.pck").write_bytes(fixture())
            (root / "index.html").write_text('const GODOT_CONFIG = {"fileSizes":{"index.pck":9999}};')
            report = Path(folder) / "sizes.json"
            # Two files at exactly 100 MiB pass; two extra bytes still fail,
            # even though the human-readable total rounds to 100.00 MiB.
            for extra in (0, 1):
                with self.subTest(extra=extra), patch("compact_web.gzip.compress", return_value=bytes(50 * 2**20 + extra)):
                    if extra:
                        with self.assertRaisesRegex(SystemExit, "by 2 bytes"):
                            finish_export(root, report)
                    else:
                        finish_export(root, report)
                    self.assertEqual(json.loads(report.read_text())["gzip_total_bytes"], 100 * 2**20 + extra * 2)

    def test_profile_preserves_closeups_and_full_resolution_shadow_mask(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "assets/icons").mkdir(parents=True)
            (root / "assets/icons/christ_sinai.jpg").touch()
            (root / "project.godot").write_text("import_etc2_astc=true\n")
            for name in ("wood.jpg", "floor_normal.png", "iconostasis_christ_sinai.jpg", "hand_grip_young_lightskinned.png"):
                (root / (name + ".import")).write_text('importer="texture"\nprocess/size_limit=0\ncompress/mode=0\ncompress/lossy_quality=0.7\ndetect_3d/compress_to=1\nmipmaps/generate=false\n')
            mask = root / "nave_shadow.png.import"
            mask.write_text('importer="2d_array_texture"\ncompress/mode=2\nslices/vertical=2\n')
            light = root / "nave.exr.import"
            light.write_text('importer="2d_array_texture"\ncompress/mode=2\nslices/vertical=8\n')
            prepare(root)
            self.assertIn("process/size_limit=512", (root / "wood.jpg.import").read_text())
            for name in ("iconostasis_christ_sinai.jpg", "hand_grip_young_lightskinned.png"):
                self.assertIn("process/size_limit=1024", (root / (name + ".import")).read_text())
                self.assertIn("mipmaps/generate=true", (root / (name + ".import")).read_text())
            self.assertIn("compress/mode=2", (root / "floor_normal.png.import").read_text())
            self.assertEqual(mask.read_text(), 'importer="2d_array_texture"\ncompress/mode=0\nslices/vertical=2\n')
            self.assertEqual(light.read_text(), 'importer="2d_array_texture"\ncompress/mode=2\nslices/vertical=8\n')


if __name__ == "__main__":
    unittest.main()
