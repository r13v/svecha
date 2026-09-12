"""Original synthesized foley for the prototype; Python standard library only."""
import math
import random
import struct
import wave
from pathlib import Path

FOLDER = Path(__file__).resolve().parents[1] / 'game/assets/audio'
FOLDER.mkdir(exist_ok=True)
RATE = 22050
rng = random.Random(73)

def save(name, samples):
    with wave.open(str(FOLDER / f'{name}.wav'), 'wb') as wav:
        wav.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        wav.writeframes(b''.join(struct.pack('<h', int(max(-1, min(1, v)) * 32767)) for v in samples))

for name, duration in [('footstep', 0.3), ('door', 1.0), ('wax_contact', 0.15)]:
    samples = []
    low = 0
    for i in range(int(RATE * duration)):
        t = i / RATE
        low = low * 0.80 + rng.uniform(-1, 1) * 0.20
        if name == 'footstep':
            value = (low * 0.65 + math.sin(t * math.tau * 95) * 0.18) * math.exp(-t * 23) * min(t * 500, 1)
        elif name == 'door':
            phase = math.tau * (160 * t + 25 * math.sin(t * 3))
            value = (math.sin(phase) * 0.13 + low * 0.18) * math.sin(math.pi * t / duration) ** 2
        else:
            value = low * 0.4 * math.exp(-t * 45) * min(t * 800, 1)
        samples.append(value)
    save(name, samples)
# Gentle periodic outdoor air. Harmonics make the loop continuous.
wind = [sum(math.sin(math.tau * k * i / (RATE * 12) + k * 1.37) / k for k in range(19, 120, 3)) * 0.6 for i in range(RATE * 12)]
save('air', wind)
print('AUDIO_BUILT 4')
