import pyttsx3

engine = pyttsx3.init()
voices = engine.getProperty('voices')

print("--- DANH SÁCH GIỌNG NÓI ---")
for voice in voices:
    print(f"Tên: {voice.name}")
    print(f"ID: {voice.id}")
    print("-------------------------")

# Thử nói luôn để check
print("Đang thử nói...")
engine.say("Xin chào, tôi là Emo, tôi đã nói được tiếng Việt.")
engine.runAndWait()