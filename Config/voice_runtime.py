"""Pinned optional runtime, outside the application and production data."""
from pathlib import Path

VERSION = "1.9.4"
RUNTIME_NAME = "whisper-v1.9.4-base"
SOURCE_URL = "https://codeload.github.com/ggml-org/whisper.cpp/tar.gz/refs/tags/v1.9.4"
SOURCE_SHA256 = "57e280cee375ab02425b806ad5146b99f6eb9357e3c2b31357c8a6af2e2e44ae"
MODEL_FILENAME = "ggml-base.bin"
MODEL_MAX_BYTES = 150 * 1024 * 1024
MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin"
MODEL_SHA256 = "60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe"


def runtime_dir():
    return Path.home() / ".local/share/homehub/voice" / RUNTIME_NAME
