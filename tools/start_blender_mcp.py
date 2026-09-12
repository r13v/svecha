"""Run with Blender --factory-startup --python; affects only this process."""

import importlib.util
import os
import socket
import sys
from pathlib import Path

import bpy

if bpy.app.background:
    raise RuntimeError("Blender MCP needs a GUI event loop. Start without --background.")
with socket.socket() as probe:
    if probe.connect_ex(("127.0.0.1", 9876)) == 0:
        raise RuntimeError("Port 9876 is already in use. Reuse or close the existing Blender MCP window.")

addon = Path(__file__).resolve().parents[1] / ".tools/blender_mcp_addon.py"
if not addon.is_file():
    raise RuntimeError("Run ./tools/setup.sh first.")
os.environ["BLENDER_MCP_DISABLE_TELEMETRY"] = "1"
spec = importlib.util.spec_from_file_location("candle_blender_mcp", addon)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
module.register()
bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.scene.unit_settings.scale_length = 1.0
if not bpy.types.blendermcp_server.running:
    raise RuntimeError("Blender MCP did not start; inspect the Blender log.")
print("CANDLE_BLENDER_MCP_READY", bpy.app.version_string, flush=True)
