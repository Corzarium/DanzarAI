# tts.py

from TTS.api import TTS
from pydub import AudioSegment
import winsound
import os

# initialize once
tts = TTS(model_name="tts_models/en/vctk/vits", progress_bar=False, gpu=False)

def make_wav(text: str, filename: str = "ai_response.wav") -> str:
    """
    Synthesize `text` to a WAV file on disk and return its filename.
    """
    tts.tts_to_file(text=text, speaker="p231", file_path=filename)
    return filename

def play_wav(path: str):
    """
    Play the WAV file at `path` using the Windows winsound API.
    """
    # ensure file exists
    if not os.path.isfile(path):
        raise FileNotFoundError(f"{path} not found")
    # this blocks until playback is done
    winsound.PlaySound(path, winsound.SND_FILENAME)
