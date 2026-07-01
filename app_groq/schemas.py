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
    missing_mandatory_documents: List[str]
    missing_optional_documents: List[str]
    is_eligible_for_review: bool


class AgentAOutput(BaseModel):
    """Toàn bộ output mà Agent A gửi sang Agent B."""
    success: bool
    loan_profile_type: Optional[str] = None          # có thể None nếu Agent A lỗi sớm
    validation_results: Optional[ValidationResults] = None   # có thể None nếu lỗi
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
    recommendations: List[str]


# ── Human-in-the-loop ──────────────────────────────────────────────────────────

class ApprovalDecision(BaseModel):
    """Body gửi lên khi user xác nhận (approve/reject) nội dung LLM sinh ra."""
    approve: bool
    edited_llm_output: Optional[Dict[str, Any]] = None   # nếu user sửa lại nội dung trước khi approve
    feedback: Optional[str] = None                        # lý do nếu reject


class PendingApprovalResponse(BaseModel):
    """Trả về khi graph dừng lại chờ user duyệt."""
    status: str = "pending_approval"
    thread_id: str
    llm_output: Dict[str, Any]
    message: str = "Vui lòng xem lại nội dung và gọi API resume với quyết định approve/reject."


class CompletedResponse(BaseModel):
    """Trả về khi graph đã chạy xong (approve thành công hoặc lỗi Agent A)."""
    status: str = "completed"
    result: AgentBOutput


class RejectedResponse(BaseModel):
    """Trả về khi user reject."""
    status: str = "rejected"
    thread_id: str
    feedback: Optional[str] = None
    message: str = "Report đã bị từ chối. Có thể sửa lại llm_output và gọi resume lại, hoặc hủy phiên."