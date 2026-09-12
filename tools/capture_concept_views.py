"""Capture all nine views using native Godot gameplay and its interaction ray."""
import argparse
import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VIEWS=[('01_approach','outside','Подход к храму','01_church_approach.png'),('02_door','door','Открытие двери','02_opening_the_door.png'),('03_interior','inside','Первый взгляд внутрь','03_first_interior_view.png'),('04_taking','taking','Взятие свечи','04_taking_a_candle.png'),('05_walk','walk','Проход по храму','05_walking_through_nave.png'),('06_stand','stand','Перед подсвечником','06_at_the_candle_stand.png'),('07_lighting','lighting','Зажигание','07_lighting_the_candle_v2.png'),('08_placing','placing','Установка','08_placing_the_candle.png'),('09_still','still','Минута тишины','09_a_moment_of_stillness.png')]
DEST=ROOT/'docs/04_BLENDER_ENV/fidelity/game_frames'
LOGS=ROOT/'.tools/fidelity'

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    source=parser.add_mutually_exclusive_group()
    source.add_argument('--app',action='store_true')
    source.add_argument('--pack',type=Path,help='Render an exported PCK with the installed Godot engine')
    parser.add_argument('--only',nargs='*');args=parser.parse_args()
    DEST.mkdir(parents=True,exist_ok=True);LOGS.mkdir(parents=True,exist_ok=True)
    manifest=DEST/'MANIFEST.json'
    records=json.loads(manifest.read_text()) if args.only and manifest.exists() else []
    for slug,view,title,reference in VIEWS:
        if args.only and view not in args.only:continue
        command=[str(ROOT/'builds/macos/Svecha.app/Contents/MacOS/Свеча')] if args.app else [str(ROOT/'tools/godot'),'--path',str(ROOT/'game')]
        if args.pack:command=[str(ROOT/'tools/godot'),'--main-pack',str(args.pack.resolve())]
        output=DEST/(slug+'.png')
        command += ['--','--view',view,'--hd','--capture',str(output)]
        logfile=LOGS/('capture-'+slug+'.log')
        with logfile.open('w') as log:result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=120)
        text=logfile.read_text()
        if result.returncode or 'ERROR:' in text or not output.exists():raise RuntimeError('Capture failed: '+str(logfile))
        renderer='Godot native; exported PCK' if args.pack else ('Godot native; packaged app' if args.app else 'Godot native; project')
        records=[record for record in records if record['view']!=view]
        records.append({'view':view,'title':title,'image':str(output.relative_to(ROOT)),'reference':'docs/02_CONCEPT_ART/generated_images/'+reference,'renderer':renderer})
        records.sort(key=lambda record:record['image'])
        manifest.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
        print('CAPTURE_READY',slug,flush=True)
