import pygame
from yt_dlp import YoutubeDL
from utils import log
import os
import glob
import sys

class MusicPlayer:
    def __init__(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100)
            log("PLAYER", "Module MusicPlayer đã sẵn sàng.")
        except Exception as e:
            log("PLAYER_ERROR", f"Lỗi khởi tạo mixer: {e}")
            
        self.current_file = None
        self.is_loop_mode = False
        self.volume = 0.5  # Mặc định 50% (Giá trị từ 0.0 đến 1.0)
        
        # Cập nhật volume ngay khi khởi tạo
        try: pygame.mixer.music.set_volume(self.volume)
        except: pass

    def get_ffmpeg_path(self):
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        ffmpeg_path = os.path.join(base_path, 'ffmpeg.exe')
        if os.path.exists(ffmpeg_path): return ffmpeg_path
        return None

    def set_volume(self, level):
        """Đặt âm lượng cụ thể (0-100)"""
        # Chuyển từ 0-100 sang 0.0-1.0
        new_vol = max(0, min(100, int(level))) / 100.0
        self.volume = new_vol
        try:
            pygame.mixer.music.set_volume(self.volume)
            log("PLAYER", f"Đã chỉnh âm lượng: {int(self.volume*100)}%")
        except: pass

    def change_volume(self, amount):
        """Tăng/Giảm âm lượng (+10, -20...)"""
        current_percent = int(self.volume * 100)
        new_percent = current_percent + amount
        self.set_volume(new_percent)

    def play_song_from_youtube(self, song_title):
        log("PLAYER", f"Đang tìm: {song_title}...")
        self.cleanup_temp()
        ffmpeg_location = self.get_ffmpeg_path()
        if not ffmpeg_location: return False

        ydl_opts = {
            'format': 'bestaudio/best',
            'ffmpeg_location': ffmpeg_location, 
            'outtmpl': 'temp_music', 
            'noplaylist': True,
            'default_search': 'ytsearch1',
            'quiet': True,
            'no_warnings': True,
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
        }
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(song_title, download=True)
                files = glob.glob("temp_music.mp3")
                if files:
                    self.current_file = files[0]
                    self._start_playback()
                    return True
            return False
        except Exception as e:
            log("PLAYER_ERROR", f"Lỗi tải: {e}")
            return False

    def _start_playback(self):
        if self.current_file and os.path.exists(self.current_file):
            try:
                pygame.mixer.music.load(self.current_file)
                pygame.mixer.music.set_volume(self.volume) # Nhớ set lại volume khi phát mới
                loop_val = -1 if self.is_loop_mode else 0
                pygame.mixer.music.play(loops=loop_val)
            except Exception as e:
                log("PLAYER_ERROR", f"Lỗi phát: {e}")

    def set_loop(self, enable=True):
        self.is_loop_mode = enable
        if self.current_file and pygame.mixer.music.get_busy():
            self._start_playback()
            
    def stop_music(self):
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            self.current_file = None
        except: pass
    
    def pause_music(self):
        """Tạm dừng nhạc"""
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            log("PLAYER", "Đã tạm dừng nhạc.")

    def unpause_music(self):
        """Phát tiếp nhạc"""
        # unpause chỉ có tác dụng nếu nhạc đang bị pause
        pygame.mixer.music.unpause()
        log("PLAYER", "Tiếp tục phát nhạc.")

    def is_playing(self):
        try: return pygame.mixer.music.get_busy()
        except: return False
    
    def cleanup_temp(self):
        try:
            self.stop_music()
            for f in glob.glob("temp_music.*"):
                try: os.remove(f)
                except: pass
        except: pass

def clean_temp_music():
    MusicPlayer().cleanup_temp()