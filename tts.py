from TTS.api import TTS
from pydub import AudioSegment
import os

tts = TTS(model_name="tts_models/en/vctk/vits", progress_bar=False, gpu=False)

def make_wav(text: str, filename: str="ai_response.wav") -> str:
    tts.tts_to_file(text=text, speaker="p231", file_path=filename)
    return filename

def play_wav(path: str):
    seg = AudioSegment.from_file(path)
    seg.export("tmp.wav", format="wav")
    os.system(f"ffplay -nodisp -autoexit tmp.wav")
