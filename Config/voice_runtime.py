"""Pinned optional runtime, outside the application and production data."""
from pathlib import Path

VERSION = "1.9.4"
RUNTIME_NAME = "whisper-v1.9.4-tiny"
SOURCE_URL = "https://codeload.github.com/ggml-org/whisper.cpp/tar.gz/refs/tags/v1.9.4"
SOURCE_SHA256 = "57e280cee375ab02425b806ad5146b99f6eb9357e3c2b31357c8a6af2e2e44ae"
MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin"
MODEL_SHA256 = "be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21"


def runtime_dir():
    return Path.home() / ".local/share/homehub/voice" / RUNTIME_NAME
