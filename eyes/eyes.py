import pygame
import os
import time
import config
from utils import log
from .eye_state import EyeState

class Eyes:
    def __init__(self, screen):
        self.screen = screen
        self.current_state = EyeState.IDLE
        self.animations = {} 
        self.frame_index = 0
        self.last_update_time = time.time()
        self.frame_duration = 0.025  # Tốc độ chuyển frame (0.04s ~ 25 FPS)
        self.animation_speed = 1
        self.tick_count = 0

        self._load_all_assets()

    def _load_all_assets(self):
        # Danh sách các thư mục cần load (phải khớp với EyeState)
        states = [
            EyeState.IDLE,
            EyeState.HAPPY, 
            EyeState.SAD,
            EyeState.ANGRY,
            # Thêm các thư mục khác nếu có
        ]

        for state in states:
            folder_path = os.path.join(config.ASSETS_DIR, state)
            self.animations[state] = []

            if not os.path.exists(folder_path):
                log("EYES", f"Error: Folder not found: {folder_path}")
                continue

            # Lấy danh sách file và sắp xếp theo tên (000 -> 001 -> 002)
            file_names = sorted(os.listdir(folder_path))
            
            for file_name in file_names:
                if file_name.endswith(".png"):
                    full_path = os.path.join(folder_path, file_name)
                    try:
                        img = pygame.image.load(full_path).convert_alpha()
                        # Resize ảnh về đúng chuẩn màn hình robot để tối ưu hiệu năng
                        img = pygame.transform.scale(img, (config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
                        self.animations[state].append(img)
                    except Exception as e:
                        pass
            
            log("EYES", f"Loaded {state}: {len(self.animations[state])} frames")

    def set_state(self, state):
        if state != self.current_state and state in self.animations:
            self.current_state = state
            self.frame_index = 0 
            self.last_update_time = time.time()

    def update(self):
            current_anim = self.animations.get(self.current_state)
            
            if not current_anim:
                return

            # Tăng biến đếm mỗi lần vòng lặp chạy
            self.tick_count += 1

            # Chỉ đổi ảnh khi đếm đủ số nhịp (Sync logic)
            if self.tick_count >= self.animation_speed:
                self.tick_count = 0  # Reset biến đếm
                self.frame_index += 1 # Chuyển sang ảnh tiếp theo
                
                # Loop lại nếu hết phim
                if self.frame_index >= len(current_anim):
                    self.frame_index = 0

    def draw(self):
        current_anim = self.animations.get(self.current_state)
        
        if current_anim and len(current_anim) > 0:
            # Lấy ảnh tại frame hiện tại để vẽ
            if self.frame_index < len(current_anim):
                img = current_anim[self.frame_index]
                self.screen.blit(img, (0, 0))