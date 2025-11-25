import os
from groq import Groq
import config
from utils import log

class SpeechToText:
    def __init__(self):
        try:
            self.client = Groq(api_key=config.GROQ_API_KEY)
        except Exception as e:
            log("STT", f"Error init Groq: {e}")

    def transcribe(self, audio_filename):
        if not audio_filename or not os.path.exists(audio_filename):
            return None
            
        try:
            log("STT", "Đang dịch giọng nói...")
            with open(audio_filename, "rb") as file:
                transcription = self.client.audio.transcriptions.create(
                file=(audio_filename, file.read()),
                model="gemini-2.5-flash",
                response_format="json",
                language="vi", 
                temperature=0.0
            )
            
            text = transcription.text.strip()
            log("STT", f"Heard: {text}")
            return text
            
        except Exception as e:
            log("STT", f"Transcribe Error: {e}")
            return None