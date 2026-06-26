from pydantic import BaseModel
from typing import List, Optional


# ── Input từ Agent A ──────────────────────────────────────────────────────────

class MatchedDocument(BaseModel):
    """Một chứng từ đã được Agent A khớp thành công với checklist."""
    checklist_id: str               # Mã checklist, vd: "cccd"
    checklist_item: str             # Tên đầy đủ mục checklist
    file_assigned: str              # Tên file, vd: "01_cccd_front.png"
    actual_option_used: Optional[str] = None   # Nhánh thu nhập đã dùng
    sub_document_id: Optional[str] = None
    group: str                      # Nhóm chứng từ, vd: "1_Pháp lý nhân thân"
    status: str                     # "Valid" / "Invalid"


class ValidationResults(BaseModel):
    analysis: str
    matched_documents: List[MatchedDocument]
    missing_mandatory_documents: List[str]      # Bắt buộc còn thiếu
    missing_optional_documents: List[str]       # Tùy chọn còn thiếu
    is_eligible_for_review: bool


class AgentAOutput(BaseModel):
    """Toàn bộ output mà Agent A gửi sang Agent B."""
    success: bool
    loan_profile_type: str                      # Loại sản phẩm vay
    validation_results: ValidationResults
    error: Optional[str] = None


# ── Output của Agent B ────────────────────────────────────────────────────────

class AgentBOutput(BaseModel):
    """Report Agent B trả về cho hệ thống / người dùng."""
    loan_profile_type: str          # Kế thừa từ Agent A
    is_eligible_for_review: bool    # Kế thừa từ Agent A
    overall_assessment: str         # Đánh giá tổng thể chất lượng hồ sơ
    warning_report: str             # Nội dung cảnh báo chi tiết
    missing_mandatory_documents: List[str]   # Chứng từ bắt buộc còn thiếu (đã dịch)
    missing_optional_documents: List[str]    # Chứng từ tùy chọn còn thiếu (đã dịch)
    matched_summary: List[str]      # Tóm tắt chứng từ hợp lệ theo nhóm
    invalid_documents: List[str]    # Chứng từ có trạng thái Invalid
    recommendations: List[str]      # Đề xuất hành động tiếp theo