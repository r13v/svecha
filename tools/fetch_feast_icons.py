"""Fetch selected historical icons, retaining original images and source rights."""
import concurrent.futures
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[1]
ITEMS=[('birth_mary','Kirillo-Belozersky iconostasis 01 - Birth of Mary.jpg'),('presentation','Kirillo-Belozersky iconostasis 02 - Presentation.jpg'),('nativity','Kirillo-Belozersky iconostasis 04 - Nativity.jpg'),('baptism','Kirillo-Belozersky iconostasis 07 - Baptism.jpg'),('last_supper','Simon ushakov last supper 1685.jpg'),('transfiguration','Kirillo-Belozersky iconostasis 08 - Transfiguration.jpg'),('harrowing','Kirillo-Belozersky iconostasis 20 - Harrowing.jpg'),('thomas','Kirillo-Belozersky iconostasis 21 - Doubting Thomas.jpg'),('dormition','Kirillo-Belozersky iconostasis 24 - Dormition.jpg')]

ITEMS.append(('hodegetria_dionysius','Dionysius and Workshop - The Mother of God Hodigitria - Google Art Project.jpg'))

def fetch(item):
    slug,title=item
    page='https://commons.wikimedia.org/wiki/File:'+quote(title.replace(' ','_'))
    cache=ROOT/'.tools/fidelity'/('icon_'+slug+'.html')
    if not cache.exists():subprocess.run(['curl','-fLsS','--retry','2',page,'-o',str(cache)],check=True)
    markup=cache.read_text()
    assert 'public domain' in markup and 'PD-old' in markup, 'Review rights before using '+page
    section=markup[markup.index('class="fullImageLink"'):]
    url=html.unescape(re.search(r'<a href="([^"]+)"',section).group(1))
    path=ROOT/'game/assets/icons'/((slug if slug=='hodegetria_dionysius' else 'feast_'+slug)+'.jpg')
    if not path.exists():subprocess.run(['curl','-fLsS','--retry','2',url,'-o',str(path)],check=True)
    assert path.read_bytes()[:2]==b'\xff\xd8'
    print('ICON_READY',slug,flush=True)
    return {'file':str(path.relative_to(ROOT)),'source_page':page,'download_url':url,'size':path.stat().st_size,'author':'Simon Ushakov (1626–1686)' if slug=='last_supper' else ('Dionysius and workshop (1440–1502)' if slug=='hodegetria_dionysius' else 'Anonymous Russian icon painter, 1497'),'rights':'Public domain / PD-Art; see archived original source page','changes':'Original file unmodified; aspect ratio preserved on panel','accessed':'2026-09-12','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(fetch,ITEMS))
    path=ROOT/'game/assets/icons/sources.json'
    previous=json.loads(path.read_text());names={r['file'] for r in rows}
    path.write_text(json.dumps([r for r in previous if r['file'] not in names]+rows,ensure_ascii=False,indent=2)+'\n')
