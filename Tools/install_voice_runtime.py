"""Provision pinned local STT before app replacement; no root, audio or secrets."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Config.voice_runtime import MODEL_SHA256, MODEL_URL, SOURCE_SHA256, SOURCE_URL, runtime_dir


def digest(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def download(url, target, expected, limit):
    with urllib.request.urlopen(url, timeout=60) as response, open(target, 'wb') as output:
        total = 0
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > limit:
                raise ValueError("Download exceeds expected size bound")
            output.write(chunk)
    if digest(target) != expected:
        raise ValueError("Download SHA256 mismatch")


def install():
    target = runtime_dir()
    if target.exists():
        manifest = json.loads((target / 'manifest.json').read_text())
        if (digest(target / 'ggml-tiny.bin') != MODEL_SHA256
                or digest(target / 'whisper-cli') != manifest['executable_sha256']):
            raise ValueError("Installed runtime differs from verified files")
        print("Verified existing optional voice runtime", flush=True)
        return
    if shutil.which('g++') is None or shutil.which('make') is None:
        raise RuntimeError("Build tools required: g++ and make (application has not been stopped)")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.voice-build-', dir=target.parent) as temporary:
        staging = Path(temporary)
        archive = staging / 'source.tar.gz'
        download(SOURCE_URL, archive, SOURCE_SHA256, 50 * 1024 * 1024)
        source = staging / 'source'
        source.mkdir()
        with tarfile.open(archive) as tar:
            # Only ordinary files/directories below the pinned archive root.
            for member in tar.getmembers():
                path = Path(member.name)
                if path.is_absolute() or '..' in path.parts:
                    raise ValueError("Unsafe source archive path")
                if not (member.isfile() or member.isdir()):
                    continue
                tar.extract(member, source)
        source = source / 'whisper.cpp-1.9.4'
        cmake = shutil.which('cmake')
        if cmake is None:
            tools = staging / 'build-tools'
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check',
                            '--target', str(tools), 'cmake==3.31.6'], check=True)
            cmake = str(tools / 'cmake/data/bin/cmake')
        build = staging / 'build'
        subprocess.run([cmake, '-S', str(source), '-B', str(build), '-DCMAKE_BUILD_TYPE=Release',
                        '-DBUILD_SHARED_LIBS=OFF', '-DWHISPER_BUILD_TESTS=OFF',
                        '-DWHISPER_BUILD_EXAMPLES=ON', '-DWHISPER_CURL=OFF',
                        '-DGGML_OPENMP=OFF', '-DGGML_METAL=OFF', '-DGGML_CUDA=OFF'], check=True)
        subprocess.run(['/usr/bin/nice', '-n', '10', cmake, '--build', str(build),
                        '--target', 'whisper-cli', '--parallel', '2'], check=True)
        ready = staging / 'ready'
        ready.mkdir()
        shutil.copy2(build / 'bin/whisper-cli', ready / 'whisper-cli')
        download(MODEL_URL, ready / 'ggml-tiny.bin', MODEL_SHA256, 80 * 1024 * 1024)
        shutil.copy2(source / 'LICENSE', ready / 'LICENSE-whisper.cpp')
        (ready / 'manifest.json').write_text(json.dumps({
            'version': '1.9.4', 'source_sha256': SOURCE_SHA256, 'model_sha256': MODEL_SHA256,
            'executable_sha256': digest(ready / 'whisper-cli'),
        }, indent=2))
        os.rename(ready, target)
        print("Installed optional whisper.cpp 1.9.4 + multilingual tiny", flush=True)


if __name__ == '__main__':
    install()
