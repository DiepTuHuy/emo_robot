import sys
import os

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
from face import FaceDetector
from robot import Brain 
from voice.text_to_speech import TextToSpeech 
from voice.vad_mic import VADMicrophone        
from voice.speech_to_text import SpeechToText             
from actions.music_player import MusicPlayer, clean_temp_music
from utils.window_utils import set_always_on_top 

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

USE_AUDIO_MODE = False
is_processing = False
was_music_playing = False 
global_modules = {}

def conversation_flow():
    global is_processing, was_music_playing
    
    is_processing = True 
    
    mouth = global_modules['mouth']
    mic = global_modules['mic']
    brain = global_modules['brain']
    robot_eyes = global_modules['robot_eyes']
    music_player = global_modules['music_player']
    
    recognizer = sr.Recognizer()

    try:
        log("BOT", "Đang nghe...")
        robot_eyes.set_state(EyeState.IDLE)
        
        audio_path = mic.listen_and_save("temp_input.wav")
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
            robot_eyes.set_state(EyeState.HAPPY)

            response_stream = brain.think_stream(user_text, is_audio=False)
            
            current_emotion = EyeState.HAPPY
            sentence_buffer = ""
            
            for text_chunk, emotion_tag in response_stream:
                if text_chunk:
                    sentence_buffer += text_chunk
                    
                    music_match = re.search(r"\[PLAY_MUSIC:(.*?)\]", sentence_buffer, re.IGNORECASE)
                    if music_match:
                        song_title = music_match.group(1).strip()
                        mouth.speak(f"Ok, mở bài {song_title}!")
                        sentence_buffer = ""
                        
                        was_music_playing = False 
                        
                        music_player.play_song_from_youtube(song_title)
                        break 

                    loop_match = re.search(r"\[LOOP:\s*(ON|OFF)\]", sentence_buffer, re.IGNORECASE)
                    if loop_match:
                        mode = loop_match.group(1).upper()
                        if mode == "ON":
                            mouth.speak("Đã bật lặp lại.")
                            music_player.set_loop(True)
                        else:
                            mouth.speak("Đã tắt lặp lại.")
                            music_player.set_loop(False)
                        sentence_buffer = re.sub(r"\[LOOP:.*?\]", "", sentence_buffer)

                    vol_match = re.search(r"\[VOL:\s*(.*?)\]", sentence_buffer, re.IGNORECASE)
                    if vol_match:
                        val = vol_match.group(1).strip().upper()
                        if val == "UP":
                            music_player.change_volume(20)
                            mouth.speak("Đã tăng âm lượng.")
                        elif val == "DOWN":
                            music_player.change_volume(-20)
                            mouth.speak("Đã giảm âm lượng.")
                        elif val.isdigit():
                            num = int(val)
                            music_player.set_volume(num)
                            mouth.speak(f"Đã chỉnh âm lượng thành {num} phần trăm.")
                        sentence_buffer = re.sub(r"\[VOL:.*?\]", "", sentence_buffer)

                    stop_match = re.search(r"\[STOP_MUSIC\]", sentence_buffer, re.IGNORECASE)
                    if stop_match:
                        mouth.speak("Đã dừng phát nhạc.")
                        music_player.stop_music()
                        
                        was_music_playing = False 
                        
                        sentence_buffer = re.sub(r"\[STOP_MUSIC\]", "", sentence_buffer)

                if emotion_tag:
                    current_emotion = emotion_tag
                    robot_eyes.set_state(current_emotion)
                
                if sentence_buffer:
                    if any(c in text_chunk for c in [".", "!", "?", ",", "\n"]):
                        if sentence_buffer.strip():
                            mouth.speak(sentence_buffer.strip())
                            sentence_buffer = ""
            
            if sentence_buffer.strip():
                mouth.speak(sentence_buffer.strip())
        else:
            mouth.speak("Mình không nghe rõ.")
            robot_eyes.set_state(EyeState.IDLE)
        
    except Exception as e:
        log("ERROR", f"Lỗi: {e}")    
    
    finally:
        if was_music_playing:
            log("BOT", "Tiếp tục phát nhạc...")
            music_player.unpause_music()
            was_music_playing = False
            
        is_processing = False

def run():
    global is_processing, global_modules, was_music_playing
    
    pygame.init()
    try: pygame.mixer.init(frequency=24000) 
    except: pass
    
    log("SYSTEM", "Khởi động Fia Robot (Draggable)...")

    screen = pygame.display.set_mode(
        (config.SCREEN_WIDTH, config.SCREEN_HEIGHT), 
        pygame.NOFRAME
    )
    pygame.display.set_caption(config.WINDOW_TITLE)
    clock = pygame.time.Clock()

    set_always_on_top() 

    is_dragging = False
    offset_x = 0
    offset_y = 0

    global_modules['robot_eyes'] = Eyes(screen)
    global_modules['mouth'] = TextToSpeech()
    global_modules['mic'] = VADMicrophone()
    global_modules['brain'] = Brain()
    global_modules['music_player'] = MusicPlayer()
    
    global_modules['robot_eyes'].set_state(EyeState.IDLE)
    global_modules['camera'] = FaceDetector()
    global_modules['camera'].start()

    global_modules['mouth'].speak("Chào bạn! Fia đã sẵn sàng.")

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
                    win_x, win_y = win_rect[0], win_rect[1]
                    offset_x = mx - win_x
                    offset_y = my - win_y

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    is_dragging = False

            elif event.type == pygame.MOUSEMOTION:
                if is_dragging:
                    mx, my = win32api.GetCursorPos()
                    new_x = mx - offset_x
                    new_y = my - offset_y
                    hwnd = pygame.display.get_wm_info()['window']
                    win32gui.SetWindowPos(
                        hwnd, 0, 
                        new_x, new_y, 0, 0, 
                        win32con.SWP_NOSIZE | win32con.SWP_NOZORDER
                    )

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

        if not is_processing and not global_modules['mouth'].is_speaking() and not global_modules['music_player'].is_playing():
            if global_modules['camera'].face_detected:
                if global_modules['robot_eyes'].current_state != EyeState.HAPPY:
                    global_modules['robot_eyes'].set_state(EyeState.HAPPY)
            else:
                if global_modules['robot_eyes'].current_state != EyeState.SAD:
                    global_modules['robot_eyes'].set_state(EyeState.SAD)

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