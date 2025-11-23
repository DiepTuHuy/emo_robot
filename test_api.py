import os
import sys
from google.generativeai import GenerativeModel, configure
import config
from utils import log

try:
    log("SYSTEM", "--- KIỂM TRA KẾT NỐI GEMINI ---")
    if not config.GEMINI_API_KEY:
        log("SYSTEM", "❌ Lỗi: API Key chưa được điền trong config.py")
        sys.exit()
    
    # 1. Cấu hình
    configure(api_key=config.GEMINI_API_KEY)
    model = GenerativeModel('gemini-1.5-flash')
    
    # 2. Gửi yêu cầu test không streaming
    response = model.generate_content("Trả lời rất ngắn: Chào bạn.", stream=False)
    
    # 3. Kiểm tra phản hồi
    if response.text and len(response.text) > 0:
        log("SYSTEM", "✅ Kết nối thành công!")
        log("SYSTEM", f"   Phản hồi mẫu: {response.text.strip()[:30]}...")
    else:
        # Lỗi 403/Quota sẽ nằm ở đây
        log("SYSTEM", "❌ Lỗi API: Kết nối thất bại hoặc key hết hạn/quá tải.")

except Exception as e:
    log("SYSTEM", f"❌ Lỗi kỹ thuật: Không thể kết nối. Chi tiết: {e}")