import pygame
import os

def set_always_on_top():
    """Ghim cửa sổ Pygame lên trên cùng các ứng dụng khác"""
    if os.name == 'nt':
        try:
            import win32gui
            import win32con
            
            hwnd = pygame.display.get_wm_info()['window']
            
            win32gui.SetWindowPos(
                hwnd, 
                win32con.HWND_TOPMOST, 
                0, 0, 0, 0, 
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
            )
            print("[SYSTEM] Đã ghim Fia lên màn hình.")
            
        except Exception as e:
            print(f"[SYSTEM] Lỗi khi ghim cửa sổ (Cần cài pywin32): {e}")