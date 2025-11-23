import pygame
from actions.music_player import MusicPlayer
import time
import os

# Khởi tạo player
player = MusicPlayer()
print("Đang test nhạc...")

# Thử mở một bài hát nổi tiếng
success = player.play_song_from_youtube("Son Tung M-TP Nơi này có anh official")

if success:
    print("✅ Nhạc đã mở thành công! Chờ 10 giây rồi dừng.")
    time.sleep(10)
    player.stop_music()
    # Dọn dẹp file tạm
    for f in os.listdir(os.getcwd()):
        if f.startswith('temp_music_') and f.endswith('.mp3'):
            os.remove(f)
            
else:
    print("❌ Lỗi: Không thể phát nhạc. Kiểm tra kết nối mạng và log lỗi.")