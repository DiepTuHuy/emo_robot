import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SCREEN_WIDTH = 240
SCREEN_HEIGHT = 240
FPS = 60
WINDOW_TITLE = "Emo Robot Simulator"

COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets', 'eyes')