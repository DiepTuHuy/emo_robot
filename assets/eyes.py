import pygame
import cv2
import os
import time
from utils import log
from .eye_state import EyeState
import config

class Eyes:
    def __init__(self, screen):
        self.screen = screen
        self.current_state = EyeState.IDLE
        
        # Biến quản lý trạng thái chờ (cho Outro)
        self.next_state_pending = None 
        
        # Biến video
        self.cap = None             
        self.current_video_type = "intro" 
        self.video_paths = {}       
        self.current_surface = None
        
        self.load_video_paths()
        
        # Bắt đầu
        self.set_state_immediate(EyeState.IDLE)

    def load_video_paths(self):
        # ... (Phần tìm folder assets giữ nguyên như cũ) ...
        current_dir = os.path.dirname(os.path.abspath(__file__))
        image_assets_path = os.path.join(current_dir, "eyes")
        if not os.path.exists(image_assets_path):
             project_root = os.path.dirname(os.path.dirname(current_dir)) 
             image_assets_path = os.path.join(project_root, "assets", "eyes")
             if not os.path.exists(image_assets_path):
                 image_assets_path = os.path.join(project_root, "eyes")

        log("EYES", f"Video Path: {image_assets_path}")

        states_map = {
            EyeState.IDLE: "static",   
            EyeState.HAPPY: "happy",   
            EyeState.SAD: "sad",
            EyeState.ANGRY: "angry",   
            EyeState.DISDAIN: "disdain"
        }

        for state_enum, file_prefix in states_map.items():
            # Thêm key 'outro'
            self.video_paths[state_enum] = {"intro": None, "loop": None, "outro": None}
            
            p_intro = os.path.join(image_assets_path, f"{file_prefix}_intro.mp4")
            p_loop = os.path.join(image_assets_path, f"{file_prefix}_loop.mp4")
            p_outro = os.path.join(image_assets_path, f"{file_prefix}_outro.mp4") # <--- Thêm dòng này
            
            if os.path.exists(p_intro): self.video_paths[state_enum]["intro"] = p_intro
            if os.path.exists(p_loop): self.video_paths[state_enum]["loop"] = p_loop
            if os.path.exists(p_outro): self.video_paths[state_enum]["outro"] = p_outro # <--- Load outro

            # Fallback logic
            if not self.video_paths[state_enum]["intro"] and self.video_paths[state_enum]["loop"]:
                 self.video_paths[state_enum]["intro"] = self.video_paths[state_enum]["loop"]

    def set_state(self, new_state):
        """Hàm này được gọi từ main.py"""
        if new_state == self.current_state:
            return

        # LOGIC XỬ LÝ OUTRO:
        # Kiểm tra xem trạng thái hiện tại có Outro không?
        current_outro_path = self.video_paths[self.current_state].get("outro")
        
        if current_outro_path and self.current_video_type != "outro":
            # Nếu có Outro -> Chạy Outro trước, lưu state mới vào hàng đợi
            log("EYES", f"Playing Outro for {self.current_state} -> Waiting for {new_state}")
            self.next_state_pending = new_state
            self.play_video(self.current_state, "outro")
        else:
            # Nếu không có Outro -> Chuyển ngay lập tức (Cắt cái rụp)
            self.set_state_immediate(new_state)

    def set_state_immediate(self, new_state):
        """Chuyển trạng thái ngay lập tức (Bỏ qua Outro)"""
        self.current_state = new_state
        self.next_state_pending = None
        self.play_video(new_state, "intro")

    def play_video(self, state, v_type):
        if state not in self.video_paths: return

        path = self.video_paths[state].get(v_type)
        if not path:
            # Logic nhảy cóc nếu thiếu file
            if v_type == "intro": self.play_video(state, "loop")
            elif v_type == "outro": self.set_state_immediate(self.next_state_pending) # Skip outro
            return

        if self.cap: self.cap.release()
        self.current_video_type = v_type
        self.cap = cv2.VideoCapture(path)

    def update(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            
            if ret:
                frame = cv2.resize(frame, (config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = frame.swapaxes(0, 1)
                self.current_surface = pygame.surfarray.make_surface(frame)
            else:
                # --- XỬ LÝ KHI HẾT VIDEO ---
                if self.current_video_type == "intro":
                    # Hết Intro -> Sang Loop
                    self.play_video(self.current_state, "loop")
                    
                elif self.current_video_type == "loop":
                    # Hết Loop -> Nếu có lệnh đổi state thì chạy Outro, không thì lặp lại
                    if self.next_state_pending:
                         # (Trường hợp hiếm: Lệnh đổi state đến đúng lúc hết loop)
                         self.play_video(self.current_state, "outro")
                    else:
                        # Replay Loop
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        
                elif self.current_video_type == "outro":
                    # Hết Outro -> Chuyển sang Intro của State mới đang chờ
                    if self.next_state_pending:
                        log("EYES", f"Outro finished. Switching to {self.next_state_pending}")
                        self.set_state_immediate(self.next_state_pending)
                    else:
                        # Fallback an toàn (về IDLE)
                        self.set_state_immediate(EyeState.IDLE)

    def draw(self):
        if self.current_surface:
            self.screen.blit(self.current_surface, (0, 0))