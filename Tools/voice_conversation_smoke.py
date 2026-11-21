"""Pi-only synthetic speech round trip. Does not open a microphone or speaker."""
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Adapters.piper_tts import PiperTts
from Adapters.whisper_cpp_adapter import WhisperCppAdapter, HOME_VOCABULARY
from App.voice_activity import is_toggle
from Config.voice_runtime import runtime_dir, MODEL_FILENAME


async def main():
    speaker = PiperTts()
    transcriber = WhisperCppAdapter(runtime_dir() / 'whisper-cli', runtime_dir() / MODEL_FILENAME,
        max_seconds=30, prompt=HOME_VOCABULARY + ' Hasło: Klopsy.')
    try:
        pcm, fmt = await speaker.synthesize('Klopsy.')
        result = await transcriber.transcribe(pcm, fmt)
        print(f'Synthetic wake phrase: {result.text!r}; STT {result.seconds:.2f}s', flush=True)
        if not is_toggle(result.text):
            raise RuntimeError('The installed Polish STT did not recognize the synthetic wake phrase')
        print('Wake phrase round trip passed; physical microphone/speaker still require a user test.')
    finally:
        await speaker.aclose()


if __name__ == '__main__':
    asyncio.run(main())
