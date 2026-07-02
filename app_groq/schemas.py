from pydantic import BaseModel
from typing import List, Optional, Dict, Any


# ── Input từ Agent A ──────────────────────────────────────────────────────────

class MatchedDocument(BaseModel):
    checklist_id: str
    checklist_item: str
    file_assigned: str
    actual_option_used: Optional[str] = None
    sub_document_id: Optional[str] = None
    group: str
    status: str


class ValidationResults(BaseModel):
    analysis: str
    matched_documents: List[MatchedDocument]
    # Giờ là list tên tiếng Việt đầy đủ (string), không còn là list ID
    missing_mandatory_documents: List[str]
    missing_optional_documents: List[str]
    is_eligible_for_review: bool


# ── Cross-check (mới từ Agent A v2) ──────────────────────────────────────────

class FieldValue(BaseModel):
    """Một giá trị của field trong một file cụ thể."""
    file_name: str
    document_id: str
    value: str


class ConflictItem(BaseModel):
    """Một mâu thuẫn dữ liệu được phát hiện khi kiểm tra chéo."""
    field_name: str
    values: List[FieldValue]
    majority_value: Optional[str] = None        # None nếu không có đa số
    conflicting_files: List[str]
    reason: str


class CrossCheckResults(BaseModel):
    is_consistent: bool
    conflicts_found: List[ConflictItem] = []    # rỗng nếu không có mâu thuẫn


class AgentAOutput(BaseModel):
    """Toàn bộ output mà Agent A gửi sang Agent B."""
    success: bool
    loan_profile_type: Optional[str] = None
    validation_results: Optional[ValidationResults] = None
    cross_check_results: Optional[CrossCheckResults] = None   # ← field mới
    error: Optional[str] = None


# ── Output của Agent B ────────────────────────────────────────────────────────

class AgentBOutput(BaseModel):
    loan_profile_type: str
    is_eligible_for_review: bool
    overall_assessment: str
    warning_report: str
    missing_mandatory_documents: List[str]
    missing_optional_documents: List[str]
    matched_summary: List[str]
    invalid_documents: List[str]
    # Thêm phần cross-check vào output để hiển thị trên UI
    cross_check_summary: List[str]
    recommendations: List[str]


# ── Human-in-the-loop ──────────────────────────────────────────────────────────

class ApprovalDecision(BaseModel):
    """Body gửi lên khi user xác nhận (approve/reject) nội dung LLM sinh ra."""
    approve: bool
    edited_llm_output: Optional[Dict[str, Any]] = None
    feedback: Optional[str] = None


class PendingApprovalResponse(BaseModel):
    """Trả về khi graph dừng lại chờ user duyệt."""
    status: str = "pending_approval"
    thread_id: str
    llm_output: Dict[str, Any]
    message: str = "Vui lòng xem lại nội dung và gọi API resume với quyết định approve/reject."


class CompletedResponse(BaseModel):
    """Trả về khi graph đã chạy xong."""
    status: str = "completed"
    result: AgentBOutput


class RejectedResponse(BaseModel):
    """Trả về khi user reject."""
    status: str = "rejected"
    thread_id: str
    feedback: Optional[str] = None
    message: str = "Report đã bị từ chối. Có thể sửa lại llm_output và gọi resume lại, hoặc hủy phiên."