"""Download the selected CC0 PBR sources; preserve their metadata and hashes."""
import concurrent.futures
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'art/textures/pbr'
CACHE = ROOT / '.tools/fidelity'
AGENT = 'SvechaAssetPipeline/0.2 (local game authoring)'
SELECTED = ['monastery_stone_floor', 'stone_floor', 'slab_tiles', 'white_plaster_02', 'white_plaster_rough_02', 'worn_cracked_plaster',
            'wood_table_worn', 'wood_cabinet_worn_long', 'rough_wood', 'roof_slates_02',
            'wool_boucle', 'poly_wool_herringbone', 'large_floor_tiles_02', 'rock_tile_floor_02', 'sparse_grass', 'old_sandstone_02']


def fetch(url, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        subprocess.run(['curl', '-fLsS', '--retry', '2', '-A', AGENT, url, '-o', str(target)], check=True)
    return target


def material(slug):
    info_path = fetch('https://api.polyhaven.com/info/' + slug, CACHE / (slug + '_info.json'))
    files_path = fetch('https://api.polyhaven.com/files/' + slug, CACHE / (slug + '_files.json'))
    info = json.loads(info_path.read_text())
    files = json.loads(files_path.read_text())
    row = {'asset': slug, 'source': 'https://polyhaven.com/a/' + slug, 'license': 'CC0-1.0',
           'authors': info.get('authors'), 'dimensions_mm': info.get('dimensions'), 'files': {}}
    for channel in ['Diffuse', 'nor_gl', 'Rough', 'Displacement', 'AO']:
        if channel not in files: continue
        available = files[channel].get('2k', files[channel].get('1k'))
        fmt = 'jpg' if 'jpg' in available else 'png'
        entry = available[fmt]
        target = fetch(entry['url'], DEST / slug / (channel + '.' + fmt))
        assert hashlib.md5(target.read_bytes()).hexdigest() == entry['md5'], target
        row['files'][channel] = {'file': str(target.relative_to(ROOT)), 'url': entry['url'],
                                 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
    print('PBR_READY', slug, flush=True)
    return row


if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(material, SELECTED))
    manifest = DEST / 'SOURCES.json'
    manifest.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
    print('PBR_MATERIALS_READY', len(rows))
