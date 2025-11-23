import cv2
import os
import config

def extract_frames(video_path, output_folder, start_sec, end_sec):
    if not os.path.exists(video_path):
        print(f"Lỗi: Không tìm thấy file video tại {video_path}")
        return

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) 
    
    start_frame = int(start_sec * fps)
    end_frame = int(end_sec * fps)
    
    current_frame = 0
    saved_count = 0
    
    print(f"Đang xử lý... FPS của video là: {fps}")

    while True:
        ret, frame = cap.read()
        
        if not ret:
            break
            
        if current_frame >= start_frame and current_frame <= end_frame:
            
            resized_frame = cv2.resize(frame, (config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
            
            file_name = f"{saved_count:03d}.png"
            path = os.path.join(output_folder, file_name)
            
            cv2.imwrite(path, resized_frame)
            saved_count += 1
            
        current_frame += 1
        
        if current_frame > end_frame:
            break

    cap.release()
    print(f"Hoàn tất! Đã lưu {saved_count} ảnh vào thư mục: {output_folder}")

if __name__ == "__main__":
    VIDEO_FILE = "1118.mp4" 
    
    extract_frames(VIDEO_FILE, "eyes/assets/idle", start_sec=21, end_sec=28)