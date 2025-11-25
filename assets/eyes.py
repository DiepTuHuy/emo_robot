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
        
        # --- QUẢN LÝ VIDEO ---
        self.video_paths = {}       
        self.cap = None             # Chỉ dùng cho Intro/Outro (Stream từ đĩa)
        
        # --- QUẢN LÝ LOOP (RAM CACHE) ---
        # Cấu trúc: { 'idle': [Surface1, Surface2...], 'happy': [...] }
        self.loop_cache = {}        
        self.loop_index = 0         # Frame hiện tại của loop
        self.loop_direction = 1     # 1: Xuôi, -1: Ngược (Ping-pong)
        self.last_loop_time = 0
        self.loop_fps = 30          # Tốc độ chạy loop (FPS)
        
        # --- TRẠNG THÁI ---
        self.current_video_type = "intro" # intro, loop, outro
        self.next_state_pending = None 
        self.current_surface = None

        self.load_assets()
        self.set_state_immediate(EyeState.IDLE)

    def load_assets(self):
        """Load đường dẫn và Cache trước các video Loop vào RAM"""
        # 1. Tìm đường dẫn
        current_dir = os.path.dirname(os.path.abspath(__file__))
        image_assets_path = os.path.join(current_dir, "eyes")
        if not os.path.exists(image_assets_path):
             project_root = os.path.dirname(os.path.dirname(current_dir)) 
             image_assets_path = os.path.join(project_root, "assets", "eyes")
             if not os.path.exists(image_assets_path):
                 image_assets_path = os.path.join(project_root, "eyes")

        log("EYES", f"Loading assets from: {image_assets_path}")

        states_map = {
            EyeState.IDLE: "static",   
            EyeState.HAPPY: "happy",   
            EyeState.SAD: "sad",
            EyeState.ANGRY: "angry",   
            EyeState.DISDAIN: "disdain"
        }

        for state_enum, file_prefix in states_map.items():
            self.video_paths[state_enum] = {"intro": None, "outro": None}
            
            # Intro/Outro giữ nguyên là đường dẫn file (Stream)
            p_intro = os.path.join(image_assets_path, f"{file_prefix}_intro.mp4")
            p_outro = os.path.join(image_assets_path, f"{file_prefix}_outro.mp4")
            p_loop  = os.path.join(image_assets_path, f"{file_prefix}_loop.mp4")

            if os.path.exists(p_intro): self.video_paths[state_enum]["intro"] = p_intro
            if os.path.exists(p_outro): self.video_paths[state_enum]["outro"] = p_outro
            
            # CACHE LOOP VÀO RAM NGAY LẬP TỨC
            if os.path.exists(p_loop):
                log("EYES", f"Caching Loop to RAM: {file_prefix}...")
                self.loop_cache[state_enum] = self._cache_video_to_surfaces(p_loop)
            else:
                self.loop_cache[state_enum] = [] # Không có loop

            # Fallback logic: Nếu không có intro, dùng frame đầu tiên của Loop làm intro
            if not self.video_paths[state_enum]["intro"] and len(self.loop_cache[state_enum]) > 0:
                 # Hack: Intro coi như rỗng để nhảy thẳng vào Loop
                 self.video_paths[state_enum]["intro"] = "SKIP" 

    def _cache_video_to_surfaces(self, path):
        """Đọc toàn bộ video, convert sang Pygame Surface và lưu vào List"""
        frames = []
        cap = cv2.VideoCapture(path)
        while True:
            ret, frame = cap.read()
            if not ret: break
            
            # Xử lý hình ảnh (Resize -> Convert -> SwapAxes)
            frame = cv2.resize(frame, (config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = frame.swapaxes(0, 1)
            surface = pygame.surfarray.make_surface(frame)
            frames.append(surface)
        cap.release()
        return frames

    def set_state(self, new_state):
        if new_state == self.current_state: return

        # Logic Outro
        current_outro_path = self.video_paths[self.current_state].get("outro")
        if current_outro_path and self.current_video_type != "outro":
            self.next_state_pending = new_state
            self.play_stream_video(self.current_state, "outro")
        else:
            self.set_state_immediate(new_state)

    def set_state_immediate(self, new_state):
        self.current_state = new_state
        self.next_state_pending = None
        
        # Check intro
        intro_path = self.video_paths[new_state].get("intro")
        if intro_path == "SKIP" or not intro_path:
            self.start_loop_mode()
        else:
            self.play_stream_video(new_state, "intro")

    def play_stream_video(self, state, v_type):
        """Chế độ Stream (Dùng cho Intro/Outro - Chạy 1 lần)"""
        path = self.video_paths[state].get(v_type)
        if not path:
            if v_type == "intro": self.start_loop_mode()
            elif v_type == "outro": self.set_state_immediate(self.next_state_pending)
            return

        if self.cap: self.cap.release()
        self.current_video_type = v_type
        self.cap = cv2.VideoCapture(path)

    def start_loop_mode(self):
        """Chuyển sang chế độ Loop (Dùng RAM)"""
        if self.cap: 
            self.cap.release()
            self.cap = None
            
        self.current_video_type = "loop"
        self.loop_index = 0
        self.loop_direction = 1 # Bắt đầu chạy xuôi
        self.last_loop_time = time.time()

    def update(self):
        # ------------------ TRƯỜNG HỢP 1: ĐANG CHẠY INTRO / OUTRO (STREAM) ------------------
        if self.current_video_type != "loop":
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    frame = cv2.resize(frame, (config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame = frame.swapaxes(0, 1)
                    self.current_surface = pygame.surfarray.make_surface(frame)
                else:
                    # Hết video stream
                    if self.current_video_type == "intro":
                        self.start_loop_mode()
                    elif self.current_video_type == "outro":
                        if self.next_state_pending:
                            self.set_state_immediate(self.next_state_pending)
                        else:
                            self.set_state_immediate(EyeState.IDLE)
            return

        # ------------------ TRƯỜNG HỢP 2: ĐANG CHẠY LOOP (RAM CACHE) ------------------
        # Lấy danh sách frame đã cache
        frames = self.loop_cache.get(self.current_state, [])
        if not frames: return

        # Điều khiển tốc độ FPS cho Loop
        now = time.time()
        if now - self.last_loop_time > (1.0 / self.loop_fps):
            self.last_loop_time = now
            
            # Cập nhật frame
            self.current_surface = frames[self.loop_index]
            
            # --- LOGIC PING-PONG (BOOMERANG) ---
            # Giúp video siêu mượt: 0 -> 100 -> 0 -> 100
            self.loop_index += self.loop_direction
            
            # Nếu chạm đáy hoặc đỉnh thì đảo chiều
            if self.loop_index >= len(frames) - 1:
                self.loop_index = len(frames) - 1
                self.loop_direction = -1  # Quay đầu
            elif self.loop_index <= 0:
                self.loop_index = 0
                self.loop_direction = 1   # Đi tiếp

    def draw(self):
        if self.current_surface:
            self.screen.blit(self.current_surface, (0, 0))