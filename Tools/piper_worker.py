"""Private persistent CPU worker. JSON lines in, length-prefixed WAV out. No audio devices."""
import io
import json
import struct
import sys
import wave


def main():
    import onnxruntime
    from piper import PiperVoice
    from piper.config import PiperConfig
    options = onnxruntime.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    model = sys.argv[1]
    with open(model + '.json', encoding='utf-8') as config:
        voice = PiperVoice(config=PiperConfig.from_dict(json.load(config)),
            session=onnxruntime.InferenceSession(model, sess_options=options,
                                                providers=['CPUExecutionProvider']))
    while line := sys.stdin.buffer.readline(4097):
        if len(line) > 4096:
            raise ValueError('Input too long')
        text = json.loads(line)
        if not isinstance(text, str) or not 1 <= len(text) <= 400:
            raise ValueError('Invalid text')
        output = io.BytesIO()
        with wave.open(output, 'wb') as wav:
            voice.synthesize_wav(text, wav)
        audio = output.getvalue()
        if len(audio) > 3 * 1024 * 1024:
            raise ValueError('Audio too long')
        sys.stdout.buffer.write(struct.pack('!I', len(audio)) + audio)
        sys.stdout.buffer.flush()


if __name__ == '__main__':
    main()
