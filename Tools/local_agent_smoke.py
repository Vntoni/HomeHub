"""Three real Pi classifications before a long model benchmark. No device calls."""
import asyncio
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Adapters.local_intent import LocalIntentClient


async def main():
    client = LocalIntentClient()
    for text, expected in [
        ('Jak ciepło jest w salonie?', {'kind': 'temperatura', 'room': 'salon'}),
        ('Proszę powiedz mi jaka jest temperatura w salonie', {'kind': 'temperatura', 'room': 'salon'}),
        ('Sprawdź wilgotność', {'kind': 'wilgotnosc', 'room': 'unknown'}),
    ]:
        started = time.monotonic()
        actual = await client.classify(text)
        print(f'{text}: {actual}; {time.monotonic()-started:.2f}s', flush=True)
        if actual != expected:
            raise ValueError(f'Wrong intent: expected {expected}, got {actual}')


if __name__ == '__main__':
    asyncio.run(main())
