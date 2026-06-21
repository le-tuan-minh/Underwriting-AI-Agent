from pydantic import BaseModel
from typing import Any

# Dữ liệu Agent A gửi sang Agent B
class AgentAOutput(BaseModel):
    document_id: str        # Mã hồ sơ, ví dụ: "HS001"
    document_type: str      # Loại văn bản, ví dụ: "CMND", "Hợp đồng lao động"
    summary: str            # Tóm tắt nội dung văn bản
    checklist: dict         # Kết quả so sánh checklist

# Dữ liệu Agent B trả về
class AgentBOutput(BaseModel):
    document_id: str        # Mã hồ sơ (lấy từ input)
    report: str             # Nội dung report cảnh báo
    missing_documents: list # Danh sách chứng từ còn thiếu
    error_pages: list       # Danh sách trang lỗi