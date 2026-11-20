"""Compare local STT on an explicit WAV/reference manifest; never opens a mic.

Manifest: [{"wav": "relative.wav", "reference": "Polskie zdanie."}, ...]
Only counts, timing and WER are printed, not audio or recognized text.
Synthetic samples measure the pipeline, not real-world microphone accuracy.
"""
import argparse
import asyncio
import json
from pathlib import Path
import re
import statistics
import sys
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Adapters.whisper_cpp_adapter import WhisperCppAdapter, HOME_VOCABULARY
from Config.voice_runtime import MODEL_FILENAME, runtime_dir
from Ports.audio_probe import PcmFormat


def words(text):
    return re.findall(r'\w+', text.casefold())


def errors(reference, hypothesis):
    previous = list(range(len(hypothesis) + 1))
    for i, word in enumerate(reference, 1):
        current = [i]
        for j, other in enumerate(hypothesis, 1):
            current.append(min(current[-1] + 1, previous[j] + 1,
                               previous[j - 1] + (word != other)))
        previous = current
    return previous[-1]


async def benchmark(executable, model, manifest, prompt):
    worker = WhisperCppAdapter(executable, model, prompt=prompt)
    cases = json.loads(manifest.read_text())
    totals = edits = exact = 0
    times = []
    for case in cases:
        with wave.open(str(manifest.parent / case['wav']), 'rb') as wav:
            if wav.getsampwidth() != 2:
                raise ValueError('PCM16 WAV required')
            fmt = PcmFormat(wav.getframerate(), wav.getnchannels())
            pcm = wav.readframes(wav.getnframes())
        result = await worker.transcribe(pcm, fmt)
        reference, hypothesis = words(case['reference']), words(result.text)
        if not reference:
            raise ValueError('Reference must not be empty')
        edits += errors(reference, hypothesis)
        totals += len(reference)
        exact += reference == hypothesis
        times.append(result.seconds)
    if not times:
        raise ValueError('No cases')
    return {'model': model.name, 'vocabulary_prompt': bool(prompt), 'cases': len(times),
            'exact_sentences': exact, 'word_errors': edits, 'reference_words': totals,
            'wer': round(edits / totals, 4), 'median_seconds': round(statistics.median(times), 3),
            'max_seconds': round(max(times), 3)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--executable', type=Path, default=runtime_dir() / 'whisper-cli')
    parser.add_argument('--model', type=Path, default=runtime_dir() / MODEL_FILENAME)
    parser.add_argument('--without-prompt', action='store_true')
    args = parser.parse_args()
    print(json.dumps(asyncio.run(benchmark(args.executable, args.model, args.manifest,
                    '' if args.without_prompt else HOME_VOCABULARY)), ensure_ascii=False))
