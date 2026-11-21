"""Bounded energy VAD and exact spoken toggle, independent of Qt/audio devices."""
from array import array
from collections import deque
import math
import re


def is_toggle(text):
    # Punctuation/spacing can vary in Whisper; do not fuzzy-match other words.
    return isinstance(text, str) and re.sub(r'[\W_]+', '', text.casefold()) == 'klopsy'


class UtteranceBuffer:
    def __init__(self, fmt, threshold=.008, max_seconds=30, silence_seconds=.7):
        if not 8000 <= fmt.rate <= 96000 or not 1 <= fmt.channels <= 4:
            raise ValueError('Unsupported audio format')
        self.frame_size = (fmt.rate // 50) * fmt.frame_bytes  # 20 ms
        self.threshold = threshold
        if not .1 <= silence_seconds <= 3 or not 1 <= max_seconds <= 30:
            raise ValueError("Invalid utterance timing")
        self.silence_frames = round(silence_seconds * 50)
        self.max_frames = int(max_seconds * 50)
        self.pending = bytearray()
        self.preroll = deque(maxlen=12)
        self.frames = []
        self.voiced = self.quiet = 0

    def feed(self, data):
        # Device chunks are small. Never let an unexpected source allocate unbounded memory.
        if len(data) > 262144:
            raise ValueError('Audio chunk too large')
        self.pending.extend(data)
        while len(self.pending) >= self.frame_size:
            frame = bytes(self.pending[:self.frame_size])
            del self.pending[:self.frame_size]
            samples = array('h', frame)
            rms = math.sqrt(sum(x*x for x in samples) / len(samples)) / 32768
            speech = rms >= self.threshold
            if not self.frames:
                if not speech:
                    self.preroll.append(frame)
                    continue
                self.frames = list(self.preroll)
                self.preroll.clear()
            self.frames.append(frame)
            self.voiced += int(speech)
            self.quiet = 0 if speech else self.quiet + 1
            too_long = len(self.frames) >= self.max_frames
            if self.quiet >= self.silence_frames or too_long:
                result = b''.join(self.frames) if self.voiced >= 10 else None
                self.frames, self.voiced, self.quiet = [], 0, 0
                if result is not None:
                    return result, too_long
        return None
