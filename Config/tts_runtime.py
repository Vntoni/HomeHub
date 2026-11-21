from pathlib import Path

PIPER_VERSION = '1.8.0'
MODEL = 'pl_PL-gosia-medium.onnx'
REVISION = 'e9c8a39444359388adaa94255becb37a5a2b8e51'
BASE_URL = f'https://huggingface.co/rhasspy/piper-voices/resolve/{REVISION}/pl/pl_PL/gosia/medium/'
FILES = {
    MODEL: ('d322ded1f1daffeab41bbacd43d6f62ac83a4a5d4d63a297aa39f345f506b358', 70 * 1024 * 1024),
    MODEL + '.json': ('f0cc2f4f53d60274a79bf6ec9d8d17c02e188ae3c7cc170f6d308a97526c351b', 100000),
}


def runtime_dir():
    return Path.home() / '.local/share/homehub/voice/piper-1.8.0-gosia'
