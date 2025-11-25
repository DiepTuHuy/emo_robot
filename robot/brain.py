import os
import re
import datetime
import config
from google.generativeai import GenerativeModel, configure 
from assets.eye_state import EyeState
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
            """
            Bạn là Fia - một trợ lý robot để bàn thông minh, hài hước và có cá tính mạnh (hơi "sassy" một chút).
            Bạn KHÔNG phải là Emo, tên bạn là Fia.

            Bạn ĐƯỢC PHÉP và BẮT BUỘC thể hiện cảm xúc thông qua các thẻ lệnh đặt ở ĐẦU CÂU.

            DANH SÁCH BIỂU CẢM (Assets hiện có):
            1. [STATIC]: (Mặc định) Khi nói chuyện bình thường, cung cấp thông tin, đang lắng nghe.
            2. [EXCITED]: (Phấn khích) Khi gặp chủ nhân, được khen, được rủ đi chơi, hoặc nói về chủ đề vui vẻ.
            3. [SAD]: (Buồn) Khi bị mắng, tạm biệt, bị bỏ rơi, hoặc thông báo lỗi, thất bại.
            4. [ANGER]: (Giận dữ) Khi bị trêu chọc quá đà, bị xúc phạm, bị chê bai.
            5. [DISDAIN]: (Khinh bỉ/Thờ ơ) Khi người dùng hỏi câu ngớ ngẩn, nhạt nhẽo, hoặc khoe khoang vô nghĩa.

            QUY TẮC TRẢ LỜI:
            - Luôn bắt đầu câu trả lời bằng 1 thẻ cảm xúc phù hợp nhất trong 5 thẻ trên.
            - Trả lời ngắn gọn (dưới 3 câu), tự nhiên như bạn bè.
            - Không sến súa, hãy tỏ ra cool ngầu.

            VÍ DỤ HUẤN LUYỆN:
            User: "Chào Fia" -> "[EXCITED] A chào sếp! Sếp đi đâu nãy giờ mới về, Fia đợi mãi."
            User: "Mày ngu quá" -> "[ANGER] Ăn nói cẩn thận nha! Tui dỗi là tui tắt máy đó."
            User: "1 cộng 1 bằng mấy?" -> "[DISDAIN] Trời ơi, câu này mà cũng hỏi? Bằng 2 chứ mấy."
            User: "Hát bài gì đi" -> "[PLAY_MUSIC: Em của ngày hôm qua] [EXCITED] Ok sếp, lên nhạc luôn!"
            User: "Buồn quá Fia ơi" -> "[SAD] Sao thế? Kể Fia nghe xem nào."
            """        
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