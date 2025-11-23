import pyttsx3
import edge_tts
import pygame
import asyncio
import threading
import os
import time
from utils import log

class TextToSpeechOnline:
    def __init__(self):
        try:
            pygame.mixer.init(frequency=24000) 
        except:
            pass
        
        self.speaking_status = False 

    def is_speaking(self):
        return self.speaking_status

    def speak(self, text):
        if not text:
            return
        threading.Thread(target=self._run_async, args=(text,)).start()

    def _run_async(self, text):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._speak_process(text))
        loop.close()

    async def _speak_process(self, text):
        self.speaking_status = True # Bật cờ
        
        try:
            log("TTS", f"Saying (Cute): {text}")
            
            VOICE = "vi-VN-HoaiMyNeural" 
            RATE = "+20%"                
            PITCH = "+50Hz"             
            filename = "temp_voice.mp3"

            communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
            await communicate.save(filename)

            # Phát âm thanh bằng pygame
            if os.path.exists(filename):
                pygame.mixer.music.load(filename)
                pygame.mixer.music.play()
                
                # Chờ đọc xong
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                
                # Dọn dẹp
                pygame.mixer.music.unload()
                # os.remove(filename)

        except Exception as e:
            log("TTS", f"Online Error: {e}")
            
        finally:
            self.speaking_status = False # Tắt cờ khi xong
            
    def _quick_speak_thread(self, text):
        try:
            engine = pyttsx3.init()
            
            vietnamese_voice_id = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\MSTTS_V110_viVN_An"
            
            engine.setProperty('voice', vietnamese_voice_id)
            engine.setProperty('rate', 250) 
            
            log("TTS_QUICK", f"Quickly saying: {text}")
            engine.say(text)
            engine.runAndWait()
            time.sleep(0.5)
            
        except Exception as e:
            log("TTS_QUICK", f"Error: {e}")

    def is_speaking(self):
        """Trả về True nếu robot đang bận nói (đang trong luồng worker)"""
        return self.speaking_status