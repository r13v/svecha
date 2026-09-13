"""Prepare saved ElevenLabs takes for the game; no API calls or credits used."""
from array import array
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import wave

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'art/audio/elevenlabs'
OUTPUT = ROOT / 'game/assets/audio'
RATE = 44100


def prepare(name):
    is_step = name.startswith('footstep')
    # The door's motion lasts 1.05 s; retain a short natural tail after it.
    filters = ('highpass=f=75,lowpass=f=6500,atrim=end=0.38' if is_step else
               'atrim=end=1.04,atempo=0.8,highpass=f=55,lowpass=f=7000')
    samples = array('f', subprocess.check_output([
        'ffmpeg', '-v', 'error', '-i', str(SOURCE / f'{name}.mp3'),
        '-ac', '1', '-ar', str(RATE), '-af', filters, '-f', 'f32le', '-',
    ]))
    if not samples or not all(math.isfinite(v) for v in samples):
        raise ValueError(f'Invalid audio: {name}')
    # Match the body of each step, with headroom for its heel transient.
    body = samples[:int(RATE * (0.18 if is_step else 0.4))]
    rms = math.sqrt(sum(v * v for v in body) / len(body))
    peak = max(abs(v) for v in samples)
    if rms < 1e-7:
        raise ValueError(f'Silent audio: {name}')
    gain = min(10 ** ((-24 if is_step else -23) / 20) / rms,
               10 ** ((-9 if is_step else -6) / 20) / peak)
    fade_in = int(RATE * 0.003)
    fade_out = int(RATE * (0.045 if is_step else 0.08))
    pcm = [round(v * gain * min(1, i / fade_in, (len(samples) - 1 - i) / fade_out) * 32767)
           for i, v in enumerate(samples)]
    filename = 'footstep.wav' if name == 'footstep_01' else f'{name}.wav'
    target = OUTPUT / filename
    with wave.open(str(target), 'wb') as wav:
        wav.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        wav.writeframes(struct.pack(f'<{len(pcm)}h', *pcm))
    return {
        'file': str(target.relative_to(ROOT)),
        'source': str((SOURCE / f'{name}.mp3').relative_to(ROOT)),
        'generation': str((SOURCE / f'{name}.json').relative_to(ROOT)),
        'processing': filters,
        'gain_db': round(20 * math.log10(gain), 3),
        'duration_seconds': round(len(pcm) / RATE, 4),
        'peak_dbfs': round(20 * math.log10(max(abs(v) for v in pcm) / 32768), 3),
        'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    }


if __name__ == '__main__':
    # Takes 02 and 04 amplify noisy sole brushes; keep only the clean contacts.
    rows = [prepare(name) for name in ['footstep_01', 'footstep_03', 'door']]
    (SOURCE / 'processed.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
    for row in rows:
        print(row['file'], row['duration_seconds'], 's, peak', row['peak_dbfs'], 'dBFS')
