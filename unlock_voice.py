import winreg

def register_onecore_voices():
    # Đường dẫn chứa giọng nói hiện đại (Microsoft An nằm ở đây)
    source_path = r"SOFTWARE\Microsoft\Speech_OneCore\Voices\Tokens"
    # Đường dẫn giọng nói cũ (Nơi Python tìm kiếm)
    target_path = r"SOFTWARE\Microsoft\Speech\Voices\Tokens"

    try:
        # Kết nối vào Registry
        hklm = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
        source_key = winreg.OpenKey(hklm, source_path)
        target_key = winreg.OpenKey(hklm, target_path, 0, winreg.KEY_ALL_ACCESS)

        print("Đang quét giọng nói ẩn...")
        
        i = 0
        while True:
            try:
                voice_name = winreg.EnumKey(source_key, i)
                # Chỉ tìm giọng Tiếng Việt hoặc Microsoft An
                if "Vietnam" in voice_name or "An" in voice_name:
                    print(f"-> Tìm thấy: {voice_name}")
                    
                    # Tạo key mới bên SAPI
                    source_subkey = winreg.OpenKey(source_key, voice_name)
                    try:
                        new_key = winreg.CreateKey(target_key, voice_name)
                        
                        # Copy toàn bộ thông số
                        j = 0
                        while True:
                            try:
                                val_name, val_data, val_type = winreg.EnumValue(source_subkey, j)
                                winreg.SetValueEx(new_key, val_name, 0, val_type, val_data)
                                j += 1
                            except OSError:
                                break
                        
                        # Copy thư mục Attributes (Quan trọng)
                        try:
                            src_attr = winreg.OpenKey(source_subkey, "Attributes")
                            dst_attr = winreg.CreateKey(new_key, "Attributes")
                            k = 0
                            while True:
                                try:
                                    a_name, a_data, a_type = winreg.EnumValue(src_attr, k)
                                    winreg.SetValueEx(dst_attr, a_name, 0, a_type, a_data)
                                    k += 1
                                except OSError:
                                    break
                        except FileNotFoundError:
                            pass
                            
                        print("   ✅ Đã kích hoạt thành công cho Python!")
                    except Exception as e:
                        print(f"   ❌ Lỗi kích hoạt: {e}")
                i += 1
            except OSError:
                break
                
        print("\nHOÀN TẤT! Hãy chạy lại file kiểm tra giọng nói.")

    except PermissionError:
        print("\n🔴 LỖI: BẠN CHƯA CHẠY VS CODE BẰNG QUYỀN ADMIN!")
        print("Hãy tắt VS Code, chuột phải chọn 'Run as Administrator' và thử lại.")
    except Exception as e:
        print(f"Lỗi khác: {e}")

if __name__ == "__main__":
    register_onecore_voices()