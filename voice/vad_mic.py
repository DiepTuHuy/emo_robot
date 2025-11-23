import webrtcvad
import pyaudio
import wave
import collections
from utils import log

class VADMicrophone:
    def __init__(self, rate=16000, chunk_duration_ms=30):
        self.rate = rate
        self.chunk_duration_ms = chunk_duration_ms
        self.chunk_size = int(rate * chunk_duration_ms / 1000)
        self.vad = webrtcvad.Vad(3)  
        self.pa = pyaudio.PyAudio()

    def _is_speech(self, frame):
        return self.vad.is_speech(frame, self.rate)

    def listen_and_save(self, filename="user_input.wav"):
        """
        Thu âm dùng VAD: Tự động ngắt khi dứt lời.
        Trả về đường dẫn file nếu thu thành công, None nếu không có tiếng.
        """
        log("VAD", "Đang lắng nghe (Chờ tiếng nói)...")
        
        stream = self.pa.open(format=pyaudio.paInt16,
                              channels=1,
                              rate=self.rate,
                              input=True,
                              frames_per_buffer=self.chunk_size)

        frames = []
        has_spoken = False           
        silence_duration = 0         
        max_silence_blocks = 15      
        
        try:
            while True:
                chunk = stream.read(self.chunk_size)
                
                try:
                    is_speech = self._is_speech(chunk)
                except:
                    is_speech = False

                if is_speech:
                    if not has_spoken:
                        log("VAD", "Phát hiện giọng nói! Đang ghi âm...")
                        has_spoken = True
                    
                    frames.append(chunk)
                    silence_duration = 0
                
                else:
                    if has_spoken:
                        frames.append(chunk)
                        silence_duration += 1
                        
                        if silence_duration > max_silence_blocks:
                            log("VAD", "Đã dứt lời. Dừng thu âm.")
                            break
                    else:
                        pass
                
                if len(frames) > 330: # ~10 giây
                     log("VAD", "Nói quá dài, tự động cắt.")
                     break

        except KeyboardInterrupt:
            pass
        finally:
            stream.stop_stream()
            stream.close()

        if len(frames) > 0:
            wf = wave.open(filename, 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(self.pa.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(frames))
            wf.close()
            return filename
        
        return None