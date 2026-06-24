from pydantic import BaseModel
from typing import List


# ── Input từ Agent A ──────────────────────────────────────────────────────────

class MatchedDocument(BaseModel):
    """Một chứng từ đã được Agent A khớp thành công với checklist."""
    checklist_item: str     # Mã mục checklist, vd: "1.1_Chung_tu_nhan_than"
    file_assigned: str      # Tên file, vd: "01_cccd_front.png"
    status: str             # Trạng thái, vd: "Valid" / "Invalid"


class AgentAOutput(BaseModel):
    """Toàn bộ output mà Agent A gửi sang Agent B."""
    analysis: str                           # Nhận xét tổng quan của Agent A
    matched_documents: List[MatchedDocument]  # Chứng từ đã khớp
    missing_documents: List[str]            # Chứng từ còn thiếu (tên mã)
    is_eligible_for_review: bool            # Đủ điều kiện thẩm định hay chưa


# ── Output của Agent B ────────────────────────────────────────────────────────

class AgentBOutput(BaseModel):
    """Report Agent B trả về cho hệ thống / người dùng."""
    is_eligible_for_review: bool    # Kế thừa từ Agent A
    overall_assessment: str         # Đánh giá tổng thể chất lượng hồ sơ
    warning_report: str             # Nội dung cảnh báo chi tiết
    missing_documents: List[str]    # Danh sách chứng từ còn thiếu (đã dịch)
    matched_summary: List[str]      # Tóm tắt chứng từ hợp lệ
    invalid_documents: List[str]    # Chứng từ có trạng thái Invalid
    recommendations: List[str]      # Đề xuất hành động tiếp theo