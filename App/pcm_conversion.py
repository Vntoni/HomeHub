"""Small bounded Int16 resampler for Piper mono output on 48 kHz USB speakers."""
from array import array


def resample_pcm(pcm, source, target):
    if (not 8000 <= source.rate <= 96000 or not 8000 <= target.rate <= 96000
            or not 1 <= source.channels <= 4 or not 1 <= target.channels <= 4
            or not pcm or len(pcm) % source.frame_bytes
            or len(pcm) > source.bytes_per_second * 40):
        raise ValueError('Invalid bounded PCM')
    samples = array('h', pcm)
    mono = [sum(samples[i:i+source.channels]) // source.channels
            for i in range(0, len(samples), source.channels)]
    count = len(mono) * target.rate // source.rate
    output = array('h')
    for i in range(count):
        index, fraction = divmod(i * source.rate, target.rate)
        left, right = mono[index], mono[min(index + 1, len(mono)-1)]
        value = left + (right-left) * fraction // target.rate
        output.extend([value] * target.channels)
    return output.tobytes()
