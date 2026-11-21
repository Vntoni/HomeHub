"""Provision isolated Piper and Polish voice on Linux ARM64, without recording audio."""
import asyncio
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Config.tts_runtime import BASE_URL, FILES, MODEL, PIPER_VERSION, runtime_dir
from Tools.install_voice_runtime import digest, download


def install():
    if platform.system() != 'Linux' or platform.machine() != 'aarch64':
        raise RuntimeError('This runtime is intended for the Raspberry Pi ARM64')
    root = runtime_dir()
    root.mkdir(parents=True, exist_ok=True)
    python = root / 'venv/bin/python'
    if not python.exists():
        subprocess.run([sys.executable, '-m', 'venv', str(root / 'venv')], check=True)
    subprocess.run([str(python), '-m', 'pip', 'install', '--disable-pip-version-check',
                    '--only-binary=:all:', f'piper-tts=={PIPER_VERSION}'], check=True)
    for filename, (sha, limit) in FILES.items():
        path = root / filename
        if path.exists() and digest(path) == sha:
            continue
        temporary = path.with_suffix(path.suffix + '.part')
        download(BASE_URL + filename, temporary, sha, limit)
        temporary.replace(path)
    shutil.copyfile(Path(__file__).with_name('piper_worker.py'), root / 'piper_worker.py')
    (root / 'ready.json').write_text(json.dumps({'piper': PIPER_VERSION,
        'voice': MODEL, 'model_sha256': FILES[MODEL][0],
        'worker_sha256': digest(root / 'piper_worker.py')}))
    async def smoke():
        from Adapters.piper_tts import PiperTts
        speaker = PiperTts(root)
        try:
            pcm, fmt = await speaker.synthesize('Gotowe. Słucham.')
            if not pcm:
                raise ValueError('No speech generated')
            print(f'Polish Piper synthesis verified: {len(pcm)/fmt.bytes_per_second:.2f}s audio; no playback')
        finally:
            await speaker.aclose()
    try:
        asyncio.run(smoke())
    except BaseException:
        (root / 'ready.json').unlink(missing_ok=True)
        raise


if __name__ == '__main__':
    install()
