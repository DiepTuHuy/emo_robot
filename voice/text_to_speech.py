import edge_tts
import pygame
import threading
import queue
import asyncio
import os
import time
from utils import log

class TextToSpeech:
    def __init__(self):
        self.queue = queue.Queue()
        self.is_running = True
        self.speaking_status = False # Cờ báo bận
        
        # Khởi tạo mixer
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=24000)
        except:
            pass

        threading.Thread(target=self._worker, daemon=True).start()
        log("TTS", "Giọng Cute Online (Sound Channel) đã sẵn sàng...")

    def is_speaking(self):
        return self.speaking_status

    def speak(self, text):
        if text:
            self.queue.put(text)

    def _worker(self):
        while self.is_running:
            try:
                text = self.queue.get(timeout=1)
                if text is None: continue
                
                self.speaking_status = True
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._process_audio(text))
                loop.close()

                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                log("TTS_ERROR", f"Lỗi luồng TTS: {e}")
            finally:
                self.speaking_status = False

    async def _process_audio(self, text):
        try:
            # Cấu hình giọng
            VOICE = "vi-VN-HoaiMyNeural"
            RATE = "+25%"
            PITCH = "+50Hz"
            
            filename = os.path.join(os.getcwd(), f"temp_tts_{threading.get_ident()}.mp3")
            
            communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
            await communicate.save(filename)

            if os.path.exists(filename):
                # --- KHẮC PHỤC LỖI MẤT NHẠC TẠI ĐÂY ---
                # Thay vì dùng mixer.music (kênh nhạc), ta dùng mixer.Sound (kênh hiệu ứng)
                # Kênh này KHÔNG ghi đè lên bài hát đang Pause
                
                sound = pygame.mixer.Sound(filename)
                
                # Phát âm thanh trên một channel trống
                channel = sound.play()
                
                # Chờ nói xong (quan trọng)
                if channel:
                    while channel.get_busy():
                        pygame.time.Clock().tick(10)
                
                # Dọn dẹp
                try:
                    os.remove(filename)
                except:
                    pass
                # ---------------------------------------

        except Exception as e:
            log("TTS_ERROR", f"Lỗi tạo giọng: {e}")