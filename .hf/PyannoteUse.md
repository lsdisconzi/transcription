Pyannote + Hugging Face authentication quick guide

Important:
- Hugging Face SSH keys are only for git operations over SSH.
- Pyannote model downloads require an HF access token (hf_...).
- You must accept gated terms for pyannote/speaker-diarization-3.1.

1) Create token:
- https://huggingface.co/settings/tokens
- Use Read (or Fine-grained with read access to gated repos).

2) Accept pyannote gated terms:
- https://huggingface.co/pyannote/speaker-diarization-3.1

3) Login and validate:

hf auth login
hf auth whoami

4) Example use from pyannote.audio:

from pyannote.audio import Pipeline

pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")

# inference on the whole file
pipeline("file.wav")

# inference on an excerpt
from pyannote.core import Segment
excerpt = Segment(start=2.0, end=5.0)

from pyannote.audio import Audio
waveform, sample_rate = Audio().crop("file.wav", excerpt)
pipeline({"waveform": waveform, "sample_rate": sample_rate})

5) For services in this repo, set at least one of:
- PYANNOTE_AUTH_TOKEN
- HF_TOKEN
- HUGGINGFACE_HUB_TOKEN