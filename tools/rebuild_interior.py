import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_church_assets as kit
path=kit.base.REPORTS/'church_asset_build.json'
report=json.loads(path.read_text())
requested=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
for slug,builder,target,distance,size in [
 ('church_door',kit.door,(0,0,1.4),2.5,3.2),
 ('candle_table',kit.table,(0,0,.43),1,1.25),
 ('candle_tray',kit.tray,(0,0,.04),.4,.55),
 ('window_bay',kit.window_bay,(0,0,1.7),4,4),
 ('church_shell',kit.shell,(0,0,1.8),10,15),
 ('church_vault',kit.vault,(0,0,.8),10,13),
 ('iconostasis',kit.iconostasis,(0,0,1.6),5,7.5),
 ('icon_case',kit.icon_case,(0,0,1.5),2,3.5),
]:
 if requested and slug not in requested:continue
 row=kit.base.save_asset(slug,builder(),target,distance,size,render_preview=False)
 report['assets']=[a for a in report['assets'] if a['asset']!=slug]+[row]
 path.write_text(json.dumps(report,indent=2)+'\n')
 print('INTERIOR_ASSET_READY',slug,flush=True)
