# Public speech regression fixture

`jfk-5s.wav`: first five seconds (80,000 samples, PCM16 mono 16 kHz) of
[`samples/jfk.wav` in whisper.cpp v1.9.4](https://github.com/ggml-org/whisper.cpp/blob/v1.9.4/samples/jfk.wav).
Extracted with Python `wave`, without changing sample values. Source archive SHA256
is pinned in `Config/voice_runtime.py`.

This is John F. Kennedy's public-domain US presidential inaugural address,
not a user's recording. It contains English speech. The smoke runs the production
Polish configuration and requires a nonempty multiword result to detect broken
CLI output routing; it does not assess Polish recognition quality or exact wording.
The deployment test upsamples it to stereo 48 kHz in memory, exercising the same
conversion path as Qt capture. No microphone or physical speaker is opened.
