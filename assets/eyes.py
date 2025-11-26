import pygame
import cv2
import os
import time
import random
from utils import log
from assets.eye_state import EyeState 
import config

cv2.setNumThreads(0) 

class Eyes:
    def __init__(self, screen):
        self.screen = screen
        self.current_state = EyeState.IDLE
        
        # --- CACHE (RAM) ---
        self.intro_cache = {} 
        self.loop_cache = {}
        self.outro_cache = {} 
        self.state_fps = {} 
        
        # --- PLAYBACK ---
        self.current_frames = []    
        self.frame_index = 0        
        self.play_mode = "intro"    # intro / loop / outro
        self.loop_direction = 1     
        self.last_update_time = 0
        
        self.current_surface = None
        self.next_state_pending = None 
        
        # Timer cho Random Look
        self.next_random_look_time = time.time() + 5.0

        self.load_assets()
        self.set_state_immediate(EyeState.IDLE)

    def load_assets(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        possible_paths = [
            os.path.join(current_dir, "eyes"), 
            os.path.join(os.path.dirname(current_dir), "assets", "eyes"), 
            os.path.join(os.path.dirname(current_dir), "eyes") 
        ]
        image_assets_path = None
        for p in possible_paths:
            if os.path.exists(p): image_assets_path = p; break
        
        if not image_assets_path: return

        states_map = {
            EyeState.IDLE: "idle",       
            EyeState.HAPPY: "happy",   
            EyeState.SAD: "sad",
            EyeState.SCARE: "scare",
            EyeState.DISDAIN: "disdain",
            EyeState.ANGRY: "angry",
            EyeState.LOOK_LEFT: "look_left",
            EyeState.LOOK_RIGHT: "look_right",
            
            EyeState.BLINK: "idle",    
            EyeState.SLEEP: "idle",
            EyeState.LISTENING: "idle",
            EyeState.THINKING: "idle"
        }

        for state_enum, file_prefix in states_map.items():
            self.state_fps[state_enum] = 60.0
            
            p_intro = os.path.join(image_assets_path, f"{file_prefix}_intro.mp4")
            p_outro = os.path.join(image_assets_path, f"{file_prefix}_outro.mp4")
            p_loop  = os.path.join(image_assets_path, f"{file_prefix}_loop.mp4")

            # 1. Load Intro (RAM)
            if os.path.exists(p_intro):
                frames, fps = self._cache_video_to_surfaces(p_intro, max_frames=60)
                self.intro_cache[state_enum] = frames
                if fps > 0: self.state_fps[state_enum] = fps
            else:
                self.intro_cache[state_enum] = []

            # 2. Load Loop (RAM)
            if os.path.exists(p_loop):
                frames, fps = self._cache_video_to_surfaces(p_loop, max_frames=90)
                self.loop_cache[state_enum] = frames
                if self.state_fps[state_enum] == 30.0 and fps > 0:
                    self.state_fps[state_enum] = fps
            else:
                self.loop_cache[state_enum] = []

            # 3. Load Outro (RAM) - Quan trọng để chuyển cảnh mượt
            if os.path.exists(p_outro):
                frames, _ = self._cache_video_to_surfaces(p_outro, max_frames=60)
                self.outro_cache[state_enum] = frames
            else:
                self.outro_cache[state_enum] = []

    def _cache_video_to_surfaces(self, path, max_frames=90):
        frames = []
        cap = cv2.VideoCapture(path)
        fps = 60.0 # Mặc định
        
        if not cap.isOpened(): return [], 0

        # --- LẤY FPS TỪ FILE VIDEO ---
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            # Nếu FPS đọc được quá ảo (0 hoặc > 120), reset về 30
            if fps <= 0 or fps > 120: fps = 60.0
        except:
            fps = 60.0

        count = 0
        while True:
            ret, frame = cap.read()
            if not ret or count >= max_frames: break
            try:
                frame = cv2.resize(frame, (config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = frame.swapaxes(0, 1)
                frames.append(pygame.surfarray.make_surface(frame))
            except: pass
            count += 1
            
        cap.release()
        
        # QUAN TRỌNG: Phải trả về cả frames VÀ fps
        return frames, fps
    
    def set_state(self, new_state):
        if new_state == self.current_state: return

        # Kiểm tra xem trạng thái hiện tại có Outro trong RAM không
        current_outro_frames = self.outro_cache.get(self.current_state)
        
        # Nếu có Outro -> Chạy Outro trước rồi mới chuyển
        if current_outro_frames and self.play_mode != "outro":
            self.next_state_pending = new_state
            self.start_ram_playback("outro")
        else:
            # Không có outro thì đổi luôn
            self.set_state_immediate(new_state)

    def set_state_immediate(self, new_state):
        self.current_state = new_state
        self.next_state_pending = None
        
        # Ưu tiên chạy Intro
        if self.intro_cache.get(new_state):
            self.start_ram_playback("intro")
        elif self.loop_cache.get(new_state):
            self.start_ram_playback("loop")
        else:
            # Fallback về IDLE Loop
            self.current_frames = self.loop_cache.get(EyeState.IDLE, [])
            self.play_mode = "loop"
            self.frame_index = 0

    def start_ram_playback(self, mode="loop"):
        self.play_mode = mode 
        self.frame_index = 0
        self.loop_direction = 1
        self.last_update_time = time.time()
        
        if mode == "intro":
            self.current_frames = self.intro_cache.get(self.current_state, [])
        elif mode == "loop":
            self.current_frames = self.loop_cache.get(self.current_state, [])
        elif mode == "outro":
            self.current_frames = self.outro_cache.get(self.current_state, [])

    def update(self):
        if not self.current_frames: return

        target_fps = self.state_fps.get(self.current_state, 30.0)
        now = time.time()
        if now - self.last_update_time > (1.0 / target_fps):
            self.last_update_time = now
            
            safe_index = self.frame_index % len(self.current_frames)
            self.current_surface = self.current_frames[safe_index]

            # --- LOGIC PLAYBACK ---
            
            # 1. INTRO (Chạy 1 lần)
            if self.play_mode == "intro":
                self.frame_index += 1
                if self.frame_index >= len(self.current_frames):
                    # Hết Intro -> Sang Loop
                    if self.loop_cache.get(self.current_state):
                        self.start_ram_playback("loop")
                    else:
                        self.frame_index = len(self.current_frames) - 1

            # 2. OUTRO (Chạy 1 lần -> Chuyển State)
            elif self.play_mode == "outro":
                self.frame_index += 1
                if self.frame_index >= len(self.current_frames):
                    # Hết Outro -> Chuyển sang trạng thái tiếp theo
                    if self.next_state_pending:
                        self.set_state_immediate(self.next_state_pending)
                    else:
                        self.set_state_immediate(EyeState.IDLE)

            # 3. LOOP (Ping-Pong + Random Look)
            elif self.play_mode == "loop":
                self.frame_index += self.loop_direction
                
                if self.frame_index >= len(self.current_frames) - 1:
                    self.frame_index = len(self.current_frames) - 1
                    self.loop_direction = -1 
                
                elif self.frame_index <= 0:
                    self.frame_index = 0
                    self.loop_direction = 1 
                    
                    # [LOGIC MỚI] CHỈ CHUYỂN CẢNH KHI VỀ VỊ TRÍ 0 (MƯỢT MÀ)
                    self._check_and_trigger_special_actions()

    def _check_and_trigger_special_actions(self):
        """Xử lý các hành động tự động khi loop về vị trí 0"""
        
        # A. Nếu đang IDLE -> Kiểm tra Random Look
        if self.current_state == EyeState.IDLE:
            if time.time() > self.next_random_look_time:
                target_look = random.choice([EyeState.LOOK_LEFT, EyeState.LOOK_RIGHT])
                if self.intro_cache.get(target_look):
                    log("EYES", f"Auto Action: {target_look}")
                    # Chuyển sang Look Left/Right (Sẽ tự chạy Intro -> Loop)
                    self.set_state_immediate(target_look)
                    
                    # Random time cho lần tiếp theo (5s - 8s)
                    self.next_random_look_time = time.time() + random.uniform(5.0, 8.0)
        
        # B. Nếu đang LOOK LEFT/RIGHT -> Tự động quay về IDLE
        elif self.current_state in [EyeState.LOOK_LEFT, EyeState.LOOK_RIGHT]:
            # Chạy hết 1 vòng loop của Look rồi thì quay về
            # Gọi set_state để nó tự tìm Outro của Look -> Chuyển về IDLE
            self.set_state(EyeState.IDLE)

    def draw(self):
        if self.current_surface:
            try: self.screen.blit(self.current_surface, (0, 0))
            except: pass