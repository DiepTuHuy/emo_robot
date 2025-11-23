import os
import re
import datetime
import config
from google.generativeai import GenerativeModel, configure 
from eyes.eye_state import EyeState
from utils import log
import time 

class Brain:
    def __init__(self):
        self.system_instruction = self._get_system_instruction()

        try:
            if not hasattr(config, 'GEMINI_API_KEY') or not config.GEMINI_API_KEY:
                 raise ValueError("GEMINI_API_KEY missing")
            configure(api_key=config.GEMINI_API_KEY)
            self.model = GenerativeModel('gemini-2.5-flash', system_instruction=self.system_instruction) 
            log("BRAIN", "Gemini Client OK!")
            self.is_client_ready = True
        except Exception as e:
            log("BRAIN_ERROR", f"Lỗi Init: {e}")
            self.model = None
            self.is_client_ready = False
            
        self.emotion_map = {
            "HAPPY": EyeState.HAPPY, "SAD": EyeState.SAD, 
            "ANGRY": EyeState.ANGRY, "IDLE": EyeState.IDLE
        }
        
    def _get_system_instruction(self):
        return (
            "Bạn là Emo, robot AI dễ thương. Trả lời ngắn gọn (dưới 2 câu). "
            "QUAN TRỌNG: Phân tích ý định và đặt thẻ lệnh vào ĐẦU câu trả lời:\n"
            "1. Mở nhạc: [PLAY_MUSIC: Tên bài hát]\n"
            "2. Loop: [LOOP: ON] hoặc [LOOP: OFF]\n"
            "3. Âm lượng: [VOL: UP] (tăng), [VOL: DOWN] (giảm), hoặc [VOL: số] (ví dụ 50, 100).\n"
            "4. Cảm xúc: [HAPPY], [SAD], [ANGRY], [IDLE]\n"
            "5. Dừng/Tắt nhạc: [STOP_MUSIC]\n"
            "Ví dụ: [STOP_MUSIC] Ok, mình tắt nhạc ngay."
            "Ví dụ: [VOL: UP] Ok, mình tăng tiếng lên nhé!"
        )

    def _get_current_time_info(self):
        now = datetime.datetime.now()
        return f"Hệ thống: Bây giờ là {now.strftime('%H:%M')}."

    def think_stream(self, user_text, is_audio=False):
        if not self.is_client_ready:
            yield "Lỗi kết nối AI.", EyeState.SAD
            return

        contents_for_api = [
            {"role": "user", "parts": [{"text": self._get_current_time_info()}]}, 
            {"role": "user", "parts": [{"text": user_text}]}
        ]
        
        try:
            response = self.model.generate_content(contents_for_api, stream=True)
            
            buffer = ""
            for chunk in response:
                text_chunk = chunk.text or ""
                if text_chunk:
                    buffer += text_chunk
                    
                    music_match = re.search(r"\[PLAY\_MUSIC:(.*?)\]", buffer, re.IGNORECASE)
                    if music_match:
                        song_title = music_match.group(1).strip()
                        yield f"[PLAY_MUSIC:{song_title}]", EyeState.HAPPY
                        return 

                    emotion_match = re.match(r"\[(HAPPY|SAD|ANGRY|IDLE)\]", buffer, re.IGNORECASE)
                    if emotion_match:
                        emotion_tag = emotion_match.group(1)
                        final_emotion = self.emotion_map.get(emotion_tag, EyeState.HAPPY)
                        yield "", final_emotion
                        buffer = buffer.replace(emotion_match.group(0), "", 1)
                    
                    if buffer:
                         yield buffer, None
                         buffer = "" 
            
        except GeneratorExit:
            return
            
        except Exception as e:
            log("BRAIN", f"Lỗi: {e}")
            yield "Có lỗi xảy ra rồi.", EyeState.SAD