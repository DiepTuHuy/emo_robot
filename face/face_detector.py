import cv2
import threading
import time
from utils import log

class FaceDetector:
    def __init__(self):
        self.cap = None
        self.is_running = False
        self.face_detected = False
        self.last_face_time = 0

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        threading.Thread(target=self._process_video, daemon=True).start()

    def _process_video(self):
        log("VISION", "Camera started")
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

        while self.is_running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                continue

            small_frame = cv2.resize(frame, (320, 240))
            gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
            
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)

            if len(faces) > 0:
                self.face_detected = True
                self.last_face_time = time.time()
            else:
                if time.time() - self.last_face_time > 2.0:
                    self.face_detected = False
            
            time.sleep(0.05)

        if self.cap:
            self.cap.release()
        log("VISION", "Camera stopped")

    def stop(self):
        self.is_running = False