import os
import re
import datetime
import config
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from assets.eye_state import EyeState
from utils import log
import time 

class Brain:
    def __init__(self):
        # Cấu hình Safety
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        self.system_instruction = self._get_system_instruction()

        try:
            if not hasattr(config, 'GEMINI_API_KEY') or not config.GEMINI_API_KEY:
                 raise ValueError("GEMINI_API_KEY missing")
            
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(
                'gemini-2.5-flash', 
                system_instruction=self.system_instruction,
                safety_settings=self.safety_settings
            ) 
            log("BRAIN", "Gemini Client OK!")
            self.is_client_ready = True
            self.chat_session = self.model.start_chat(history=[])
            
        except Exception as e:
            log("BRAIN_ERROR", f"Lỗi Init: {e}")
            self.model = None
            self.is_client_ready = False
            
        self.emotion_map = {
            "STATIC": EyeState.IDLE,
            "EXCITED": EyeState.HAPPY,
            "SAD": EyeState.SAD, 
            "ANGER": EyeState.ANGRY, 
            "DISDAIN": EyeState.DISDAIN 
        }
        
    def _get_system_instruction(self):
        return (
            """
            Bạn là Fia - trợ lý robot để bàn thông minh.
            Tính cách: Hài hước, sắc sảo, cá tính mạnh.
            Tên bạn là Fia.

            --- QUY TẮC QUAN TRỌNG ---
            1. Mọi câu trả lời PHẢI có thẻ cảm xúc ở đầu (VD: [EXCITED]).
            2. TUYỆT ĐỐI KHÔNG tự đọc lại thẻ cảm xúc hay thẻ lệnh.
            3. HỆ THỐNG LỆNH (Viết chính xác):
               - [PLAY_MUSIC: Tên bài hát]
               - [STOP_MUSIC]
               - [VOL: UP] / [VOL: DOWN]
            """        
        )

    def _get_current_time_info(self):
        now = datetime.datetime.now()
        return f"Hệ thống: Bây giờ là {now.strftime('%H:%M')}."

    def think_stream(self, user_text, is_audio=False):
        if not self.is_client_ready:
            yield "Lỗi kết nối AI.", EyeState.SAD
            return

        full_prompt = f"{self._get_current_time_info()} User nói: {user_text}"
        
        try:
            response = self.chat_session.send_message(full_prompt, stream=True)
            
            for chunk in response:
                if chunk.text:
                    raw_text = chunk.text
                    
                    # --- BƯỚC 1: TÁCH RIÊNG LỆNH NHẠC (FIX LỖI ĐỌC TAG) ---
                    # Tìm thẻ lệnh
                    music_match = re.search(r"\[(PLAY_MUSIC|STOP_MUSIC|VOL|LOOP):(.*?)]", raw_text, re.IGNORECASE)
                    if not music_match:
                         music_match = re.search(r"\[(STOP_MUSIC|LOOP:ON|LOOP:OFF)\]", raw_text, re.IGNORECASE)

                    if music_match:
                        cmd_string = music_match.group(0)
                        
                        # 1. Trả về LỆNH RIÊNG (để Main xử lý logic)
                        # Gửi kèm HAPPY để mắt vui lên
                        yield cmd_string, EyeState.HAPPY
                        
                        # 2. XÓA LỆNH KHỎI VĂN BẢN (để Main không đọc nhầm)
                        raw_text = raw_text.replace(cmd_string, "")

                    # --- BƯỚC 2: XỬ LÝ CẢM XÚC ---
                    emotion_tag = None
                    match = re.search(r"\[(STATIC|EXCITED|SAD|ANGER|DISDAIN)\]", raw_text, re.IGNORECASE)
                    
                    if match:
                        tag_str = match.group(1).upper()
                        emotion_tag = self.emotion_map.get(tag_str, EyeState.IDLE)
                        # Xóa thẻ cảm xúc
                        raw_text = re.sub(r"\[.*?\]\s*", "", raw_text)

                    # --- BƯỚC 3: TRẢ VỀ LỜI NÓI (Đã sạch bóng các thẻ) ---
                    if raw_text.strip():
                        yield raw_text, emotion_tag
                    elif emotion_tag:
                        yield "", emotion_tag
            
        except Exception as e:
            log("BRAIN_ERROR", f"Lỗi Gemini: {e}")
            yield "Fia bị mất kết nối với não bộ...", EyeState.SAD