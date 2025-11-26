import pygame
import cv2
import os
import time
from utils import log
from assets.eye_state import EyeState # Đảm bảo import đúng đường dẫn
import config

cv2.setNumThreads(0)  # Giảm tải CPU khi dùng OpenCV

class Eyes:
    def __init__(self, screen):
        self.screen = screen
        self.current_state = EyeState.IDLE
        
        # --- QUẢN LÝ VIDEO ---
        self.video_paths = {}       
        self.cap = None             # Chỉ dùng cho Intro/Outro (Stream từ đĩa)
        
        # --- QUẢN LÝ LOOP (RAM CACHE) ---
        # Cấu trúc: { 'IDLE': [Surface1, Surface2...], 'HAPPY': [...] }
        self.loop_cache = {}        
        self.loop_index = 0         
        self.loop_direction = 1     
        self.last_loop_time = 0
        self.loop_fps = 30          
        
        # --- TRẠNG THÁI ---
        self.current_video_type = "intro" # intro, loop, outro
        self.next_state_pending = None 
        self.current_surface = None

        self.load_assets()
        # Khởi động ở trạng thái IDLE
        self.set_state_immediate(EyeState.IDLE)

    def load_assets(self):
        """Load đường dẫn và Cache trước các video Loop vào RAM"""
        # 1. Tìm đường dẫn assets chuẩn xác
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Thử tìm folder eyes ở các cấp thư mục khác nhau để tránh lỗi path
        possible_paths = [
            os.path.join(current_dir, "eyes"), # assets/eyes
            os.path.join(os.path.dirname(current_dir), "assets", "eyes"), # root/assets/eyes
            os.path.join(os.path.dirname(current_dir), "eyes") # root/eyes
        ]
        
        image_assets_path = None
        for p in possible_paths:
            if os.path.exists(p):
                image_assets_path = p
                break
        
        if not image_assets_path:
            log("EYES_ERROR", "Không tìm thấy thư mục 'eyes' chứa video!")
            return

        log("EYES", f"Loading assets from: {image_assets_path}")

        # Mapping Enum -> Tên file prefix
        states_map = {
            EyeState.IDLE: "idle",       
            EyeState.HAPPY: "happy",   
            EyeState.SAD: "sad",
            EyeState.ANGRY: "angry",   
            EyeState.DISDAIN: "disdain",
            EyeState.SCARE: "scare",
            EyeState.LISTENING: "idle",
            EyeState.THINKING: "idle",
            EyeState.SLEEP: "idle" # Hoặc "sleep" nếu bạn đã có file sleep_loop.mp4
        }

        for state_enum, file_prefix in states_map.items():
            self.video_paths[state_enum] = {"intro": None, "outro": None}
            
            # Đường dẫn file
            p_intro = os.path.join(image_assets_path, f"{file_prefix}_intro.mp4")
            p_outro = os.path.join(image_assets_path, f"{file_prefix}_outro.mp4")
            p_loop  = os.path.join(image_assets_path, f"{file_prefix}_loop.mp4")

            # Check tồn tại và gán path
            if os.path.exists(p_intro): self.video_paths[state_enum]["intro"] = p_intro
            if os.path.exists(p_outro): self.video_paths[state_enum]["outro"] = p_outro
            
            # --- CACHE LOOP VÀO RAM ---
            # Chỉ cache nếu file tồn tại
            if os.path.exists(p_loop):
                log("EYES", f"Caching Loop to RAM: {file_prefix}...")
                try:
                    self.loop_cache[state_enum] = self._cache_video_to_surfaces(p_loop)
                except Exception as e:
                    log("EYES_ERROR", f"Lỗi cache video {file_prefix}: {e}")
                    self.loop_cache[state_enum] = []
            else:
                self.loop_cache[state_enum] = [] # List rỗng nếu không có loop

            # Logic Fallback: Nếu không có intro riêng, dùng Frame đầu của loop làm intro giả
            # Để tránh lỗi khi chuyển cảnh
            if not self.video_paths[state_enum]["intro"]:
                 self.video_paths[state_enum]["intro"] = "SKIP" 

    def _cache_video_to_surfaces(self, path):
        """Đọc video, resize, convert sang Pygame Surface"""
        frames = []
        cap = cv2.VideoCapture(path)
        
        if not cap.isOpened():
            return []

        # --- GIỚI HẠN SỐ FRAME ĐỂ KHỞI ĐỘNG NHANH ---
        MAX_FRAMES = 90  # Chỉ lấy tối đa 90 frames (khoảng 3 giây)
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret: break
            
            # Nếu load quá nhiều rồi thì dừng lại, không load nữa cho nhẹ RAM
            if frame_count >= MAX_FRAMES:
                break

            # Resize về đúng kích thước màn hình config
            # (Quan trọng: Resize trước khi convert để nhẹ máy)
            frame = cv2.resize(frame, (config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
            
            # Convert màu BGR -> RGB (Pygame dùng RGB)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Xoay trục để khớp với Pygame Surface (Swap X, Y)
            frame = frame.swapaxes(0, 1)
            
            # Tạo Surface
            surface = pygame.surfarray.make_surface(frame)
            frames.append(surface)
            
            frame_count += 1
            
        cap.release()
        return frames

    def set_state(self, new_state):
        """Hàm gọi từ bên ngoài để đổi trạng thái"""
        if new_state == self.current_state: return

        # Kiểm tra xem trạng thái hiện tại có Outro không
        current_outro_path = self.video_paths[self.current_state].get("outro")
        
        # Nếu có Outro và đang không phải là chạy Outro -> Chạy Outro trước
        if current_outro_path and self.current_video_type != "outro":
            self.next_state_pending = new_state # Lưu trạng thái tiếp theo
            self.play_stream_video(self.current_state, "outro")
        else:
            # Không có outro thì đổi luôn
            self.set_state_immediate(new_state)

    def set_state_immediate(self, new_state):
        """Đổi trạng thái ngay lập tức (Bỏ qua Outro)"""
        self.current_state = new_state
        self.next_state_pending = None
        
        # Kiểm tra Intro
        intro_path = self.video_paths[new_state].get("intro")
        
        if intro_path == "SKIP" or not intro_path:
            # Không có intro -> Vào thẳng loop
            self.start_loop_mode()
        else:
            # Có intro -> Chạy intro
            self.play_stream_video(new_state, "intro")

    def play_stream_video(self, state, v_type):
        """Chế độ Stream (Dùng cho Intro/Outro)"""
        path = self.video_paths[state].get(v_type)
        
        # Nếu path bị sai hoặc không có -> Fallback
        if not path or path == "SKIP":
            if v_type == "intro": self.start_loop_mode()
            elif v_type == "outro": 
                if self.next_state_pending:
                    self.set_state_immediate(self.next_state_pending)
                else:
                    self.set_state_immediate(EyeState.IDLE)
            return

        # Giải phóng video cũ nếu có
        if self.cap: self.cap.release()
        
        self.current_video_type = v_type
        self.cap = cv2.VideoCapture(path)

    def start_loop_mode(self):
        """Chuyển sang chế độ Loop (Dùng RAM)"""
        # Dừng stream video nếu đang chạy
        if self.cap: 
            self.cap.release()
            self.cap = None
            
        self.current_video_type = "loop"
        self.loop_index = 0
        self.loop_direction = 1 # 1: Xuôi, -1: Ngược
        self.last_loop_time = time.time()

    def update(self):
        # --- TRƯỜNG HỢP 1: ĐANG CHẠY INTRO / OUTRO (STREAM) ---
        if self.current_video_type != "loop":
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    try:
                        frame = cv2.resize(frame, (config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        frame = frame.swapaxes(0, 1)
                        self.current_surface = pygame.surfarray.make_surface(frame)
                    except Exception:
                        pass # Bỏ qua lỗi frame hỏng
                else:
                    # Hết video stream -> Chuyển trạng thái
                    if self.current_video_type == "intro":
                        self.start_loop_mode()
                    elif self.current_video_type == "outro":
                        if self.next_state_pending:
                            self.set_state_immediate(self.next_state_pending)
                        else:
                            self.set_state_immediate(EyeState.IDLE)
            else:
                # Trường hợp cap bị lỗi null -> Force chuyển
                self.start_loop_mode()
            return

        # --- TRƯỜNG HỢP 2: ĐANG CHẠY LOOP (RAM CACHE) ---
        # Lấy danh sách frame từ RAM
        frames = self.loop_cache.get(self.current_state, [])
        
        # Nếu cache rỗng (do chưa load được hoặc lỗi), thử dùng cache IDLE
        if not frames:
             frames = self.loop_cache.get(EyeState.IDLE, [])

        if not frames: return # Vẫn không có gì để vẽ thì thôi

        # Điều khiển FPS
        now = time.time()
        if now - self.last_loop_time > (1.0 / self.loop_fps):
            self.last_loop_time = now
            
            # Cập nhật frame hiện tại để vẽ
            # (Dùng % để đảm bảo index không bao giờ vượt quá độ dài mảng)
            safe_index = self.loop_index % len(frames)
            self.current_surface = frames[safe_index]
            
            # --- LOGIC PING-PONG ---
            self.loop_index += self.loop_direction
            
            if self.loop_index >= len(frames) - 1:
                self.loop_index = len(frames) - 1
                self.loop_direction = -1  # Đảo chiều chạy ngược lại
            elif self.loop_index <= 0:
                self.loop_index = 0
                self.loop_direction = 1   # Đảo chiều chạy xuôi

    def draw(self):
        if self.current_surface:
            try:
                self.screen.blit(self.current_surface, (0, 0))
            except Exception:
                pass