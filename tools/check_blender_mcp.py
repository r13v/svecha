"""Verify MCP protocol, Blender scene access, Python, and viewport capture."""

import asyncio
import base64
import json
import tomllib
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def main():
    config = tomllib.loads((ROOT / ".codex/config.toml").read_text())["mcp_servers"]["blender"]
    output = ROOT / ".tools/checks"
    output.mkdir(parents=True, exist_ok=True)
    server = StdioServerParameters(command=config["command"], env=config["env"])
    with (output / "blender-mcp.log").open("w") as log:
        async with stdio_client(server, errlog=log) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=45)) as session:
                await session.initialize()
                names = {tool.name for tool in (await session.list_tools()).tools}
                missing = set(config["enabled_tools"]) - names
                if missing:
                    raise RuntimeError(f"Missing MCP tools: {missing}")
                for name, arguments in [
                    ("get_scene_info", {"user_prompt": "Check the project Blender connection"}),
                    ("execute_blender_code", {"code": "import bpy\nprint('CANDLE_MCP_OK', bpy.app.version_string)"}),
                    ("get_viewport_screenshot", {"max_size": 1000}),
                ]:
                    result = await session.call_tool(name, arguments)
                    text = "\n".join(block.text for block in result.content if block.type == "text")
                    if result.isError or text.startswith("Error"):
                        raise RuntimeError(f"{name}: {text}")
                    if name == "get_scene_info":
                        scene = json.loads(text)
                        if "objects" not in scene:
                            raise RuntimeError(f"Unexpected scene result: {text}")
                        (output / "blender-scene.json").write_text(json.dumps(scene, indent=2))
                    elif name == "execute_blender_code" and "CANDLE_MCP_OK" not in text:
                        raise RuntimeError(f"Python command did not complete: {text}")
                    elif name == "get_viewport_screenshot":
                        images = [block for block in result.content if block.type == "image"]
                        if not images:
                            raise RuntimeError(f"Viewport image missing: {text}")
                        suffix = ".png" if images[0].mimeType == "image/png" else ".jpg"
                        (output / ("blender-viewport" + suffix)).write_bytes(base64.b64decode(images[0].data))
                    print(f"PASS: {name}")
    print(f"MCP connection verified. Evidence: {output}")


if __name__ == "__main__":
    asyncio.run(main())
