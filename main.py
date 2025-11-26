import sys
import os
import time
import pygame
import threading
import config
import speech_recognition as sr
import re
from utils import log

import win32api
import win32gui
import win32con

from assets.eyes import Eyes
from assets.eye_state import EyeState
from face.face_detector import FaceDetector 
from robot import Brain 
from voice.text_to_speech import TextToSpeech 
from voice.vad_mic import VADMicrophone        
from actions.music_player import MusicPlayer, clean_temp_music
from utils.window_utils import set_always_on_top 

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

USE_AUDIO_MODE = False
global_modules = {}

# --- QUẢN LÝ TRẠNG THÁI ---
is_processing = False      
was_music_playing = False 
last_ai_emotion_time = 0 
AI_EMOTION_HOLD_DURATION = 4.0 

# --- BIẾN CHO LOGIC VISION MỚI ---
vision_last_face_status = False # Trạng thái frame trước (Có mặt hay không)
vision_state_start_time = 0     # Thời điểm bắt đầu trạng thái cảm xúc hiện tại
VISION_TRANSITION_TIME = 7.0    # Sau 3 giây thì chuyển cảm xúc (Vui -> Idle, Sợ -> Buồn)

def conversation_flow():
    global is_processing, was_music_playing, last_ai_emotion_time
    
    is_processing = True 
    mouth = global_modules['mouth']
    mic = global_modules['mic']
    brain = global_modules['brain']
    robot_eyes = global_modules['robot_eyes']
    music_player = global_modules['music_player']
    recognizer = sr.Recognizer()

    try:
        log("BOT", "Đang nghe...")
        # Lúc nghe thì để Idle (tập trung)
        robot_eyes.set_state(EyeState.IDLE)
        
        audio_path = mic.listen_and_save("temp_input.wav")
        
        # Lúc nghĩ cũng để Idle (hoặc Thinking nếu bạn có asset sau này)
        robot_eyes.set_state(EyeState.IDLE)
        
        user_text = ""
        if audio_path:
            try:
                with sr.AudioFile(audio_path) as source:
                    audio_data = recognizer.record(source)
                    user_text = recognizer.recognize_google(audio_data, language="vi-VN")
                    log("STT", f"Nghe được: {user_text}")
            except Exception as e:
                log("STT_ERROR", f"Lỗi dịch: {e}")

        if user_text:
            mouth.speak("Dạ?") 
            
            response_stream = brain.think_stream(user_text, is_audio=False)
            sentence_buffer = ""
            
            for text_chunk, emotion_tag in response_stream:
                # Xử lý lệnh nhạc
                music_match = re.search(r"\[(PLAY_MUSIC|STOP_MUSIC|VOL|LOOP):(.*?)]", text_chunk, re.IGNORECASE)
                if not music_match:
                     music_match = re.search(r"\[(STOP_MUSIC|LOOP:ON|LOOP:OFF)\]", text_chunk, re.IGNORECASE)

                if music_match:
                    cmd_full = music_match.group(0)
                    if "PLAY_MUSIC" in cmd_full.upper():
                        song = music_match.group(2).strip()
                        mouth.speak(f"Ok, mở bài {song}")
                        was_music_playing = False
                        music_player.play_song_from_youtube(song)
                    elif "STOP_MUSIC" in cmd_full.upper():
                        mouth.speak("Đã dừng nhạc.")
                        music_player.stop_music()
                        was_music_playing = False
                    
                    robot_eyes.set_state(EyeState.HAPPY)
                    last_ai_emotion_time = time.time()
                    text_chunk = text_chunk.replace(cmd_full, "")

                # Xử lý cảm xúc AI
                if emotion_tag:
                    log("EMOTION", f"AI Set State: {emotion_tag}")
                    robot_eyes.set_state(emotion_tag)
                    last_ai_emotion_time = time.time()

                if text_chunk:
                    sentence_buffer += text_chunk
                    if any(c in text_chunk for c in [".", "!", "?", ",", "\n"]):
                        if sentence_buffer.strip():
                            mouth.speak(sentence_buffer.strip())
                            sentence_buffer = ""
            
            if sentence_buffer.strip():
                mouth.speak(sentence_buffer.strip())
        else:
            mouth.speak("Hông nghe rõ.")
            robot_eyes.set_state(EyeState.IDLE)
        
    except Exception as e:
        log("ERROR", f"Lỗi Flow: {e}")    
    
    finally:
        if was_music_playing:
            music_player.unpause_music()
            was_music_playing = False
        is_processing = False

def run():
    global is_processing, global_modules, was_music_playing, last_ai_emotion_time
    global vision_last_face_status, vision_state_start_time
    
    pygame.init()
    try: pygame.mixer.init(frequency=24000) 
    except: pass
    
    log("SYSTEM", "Khởi động Fia Robot (Smart Vision)...")

    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.NOFRAME)
    pygame.display.set_caption(config.WINDOW_TITLE)
    clock = pygame.time.Clock()
    set_always_on_top() 

    is_dragging = False
    offset_x = 0; offset_y = 0

    global_modules['robot_eyes'] = Eyes(screen)
    global_modules['mouth'] = TextToSpeech()
    global_modules['mic'] = VADMicrophone()
    global_modules['brain'] = Brain()
    global_modules['music_player'] = MusicPlayer()
    
    global_modules['camera'] = FaceDetector()
    global_modules['camera'].start()

    global_modules['mouth'].speak("Fia đã sẵn sàng.")

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    is_dragging = True
                    mx, my = win32api.GetCursorPos()
                    hwnd = pygame.display.get_wm_info()['window']
                    win_rect = win32gui.GetWindowRect(hwnd)
                    offset_x = mx - win_rect[0]; offset_y = my - win_rect[1]
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1: is_dragging = False
            elif event.type == pygame.MOUSEMOTION:
                if is_dragging:
                    mx, my = win32api.GetCursorPos()
                    win32gui.SetWindowPos(pygame.display.get_wm_info()['window'], 0, mx - offset_x, my - offset_y, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                    global_modules['camera'].stop()
                    global_modules['music_player'].stop_music()
                    clean_temp_music()

                if event.key == pygame.K_SPACE:
                    if is_processing: continue 
                    if global_modules['music_player'].is_playing(): 
                        global_modules['music_player'].pause_music()
                        was_music_playing = True 
                    else:
                        was_music_playing = False
                    threading.Thread(target=conversation_flow).start()

        # --- LOGIC ĐIỀU KHIỂN MẮT ---
        current_time = time.time()
        is_ai_holding = (current_time - last_ai_emotion_time) < AI_EMOTION_HOLD_DURATION
        
        # Chỉ xử lý Camera khi AI không đang chiếm quyền (Vui/Giận từ hội thoại) và không đang xử lý
        if not is_processing and not is_ai_holding:
            
            face_detected = global_modules['camera'].face_detected
            eyes_module = global_modules['robot_eyes']
            
            # 1. PHÁT HIỆN SỰ THAY ĐỔI (Edge Detection)
            if face_detected and not vision_last_face_status:
                # Vừa mới thấy mặt -> Vui ngay lập tức
                log("VISION", "Thấy chủ nhân -> HAPPY")
                eyes_module.set_state(EyeState.HAPPY)
                vision_state_start_time = current_time
                
            elif not face_detected and vision_last_face_status:
                # Vừa mới mất dấu -> Hoảng sợ ngay lập tức
                log("VISION", "Mất dấu chủ nhân -> SCARE")
                eyes_module.set_state(EyeState.SCARE)
                vision_state_start_time = current_time

            # 2. DUY TRÌ TRẠNG THÁI (State Duration)
            else:
                elapsed = current_time - vision_state_start_time
                
                if face_detected:
                    # Đang nhìn thấy mặt
                    if eyes_module.current_state == EyeState.HAPPY and elapsed > VISION_TRANSITION_TIME:
                        # Đã vui đủ 3 giây -> Chuyển sang Idle (Bình tĩnh)
                        if eyes_module.current_state != EyeState.IDLE:
                            eyes_module.set_state(EyeState.IDLE)
                            
                else:
                    # Không thấy mặt
                    if eyes_module.current_state == EyeState.SCARE and elapsed > VISION_TRANSITION_TIME:
                        # Đã sợ đủ 3 giây -> Chuyển sang Sad (Buồn)
                        if eyes_module.current_state != EyeState.SAD:
                            eyes_module.set_state(EyeState.SAD)

            # Cập nhật trạng thái cũ để so sánh vòng sau
            vision_last_face_status = face_detected

        global_modules['robot_eyes'].update() 
        screen.fill(config.COLOR_BLACK)
        global_modules['robot_eyes'].draw()
        pygame.display.flip()
        clock.tick(config.FPS)

    global_modules['camera'].stop()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    run()