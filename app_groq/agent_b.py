import os
import json
import uuid
from typing import TypedDict, List, Dict, Optional
from groq import Groq
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from app_groq.schemas import AgentAOutput, AgentBOutput, MatchedDocument

load_dotenv()

# ── Groq client ────────────────────────────────────────────────────────────────
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

GROQ_MODEL              = "llama-3.3-70b-versatile"
GROQ_INPUT_COST_PER_1M  = 0.59
GROQ_OUTPUT_COST_PER_1M = 0.79


# ── GraphState ────────────────────────────────────────────────────────────────

class GraphState(TypedDict):
    loan_profile_type: str
    analysis: str
    matched_documents: List[MatchedDocument]
    missing_mandatory_documents: List[str]
    missing_optional_documents: List[str]
    is_eligible_for_review: bool

    valid_docs: List[str]
    invalid_docs: List[str]
    docs_by_group: Dict[str, List[str]]
    doc_stats: dict
    risk_level: str

    llm_output: dict
    human_feedback: Optional[dict]     # lưu quyết định approve/reject gần nhất

    overall_assessment: str
    warning_report: str
    missing_mandatory_vi: List[str]
    missing_optional_vi: List[str]
    matched_summary: List[str]
    recommendations: List[str]


# ══════════════════════════════════════════════════════════════════════════════
# NODE 1 — input_parser
# ══════════════════════════════════════════════════════════════════════════════

def input_parser(state: GraphState) -> GraphState:
    valid_docs   = [d.file_assigned for d in state["matched_documents"] if d.status == "Valid"]
    invalid_docs = [d.file_assigned for d in state["matched_documents"] if d.status != "Valid"]

    docs_by_group: Dict[str, List[str]] = {}
    for d in state["matched_documents"]:
        docs_by_group.setdefault(d.group, []).append(f"{d.file_assigned} ({d.checklist_item})")

    return {**state, "valid_docs": valid_docs, "invalid_docs": invalid_docs, "docs_by_group": docs_by_group}


# ══════════════════════════════════════════════════════════════════════════════
# NODE 2 — document_analyzer
# ══════════════════════════════════════════════════════════════════════════════

def document_analyzer(state: GraphState) -> GraphState:
    total_matched   = len(state["matched_documents"])
    total_valid     = len(state["valid_docs"])
    total_invalid   = len(state["invalid_docs"])
    total_mandatory_missing = len(state["missing_mandatory_documents"])
    total_optional_missing  = len(state["missing_optional_documents"])
    total_required  = total_valid + total_mandatory_missing

    completion_rate = round(total_valid / total_required * 100, 1) if total_required > 0 else 0.0

    doc_stats = {
        "total_matched": total_matched,
        "total_valid": total_valid,
        "total_invalid": total_invalid,
        "total_mandatory_missing": total_mandatory_missing,
        "total_optional_missing": total_optional_missing,
        "completion_rate": completion_rate,
    }

    if not state["is_eligible_for_review"] or completion_rate < 50:
        risk_level = "HIGH"
    elif completion_rate < 75 or total_invalid > 0 or total_mandatory_missing > 0:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {**state, "doc_stats": doc_stats, "risk_level": risk_level}


# ══════════════════════════════════════════════════════════════════════════════
# NODE 3 — risk_assessor  ⚡ LLM call (Groq)
# ══════════════════════════════════════════════════════════════════════════════

def risk_assessor(state: GraphState) -> GraphState:
    stats    = state["doc_stats"]
    eligible = "ĐỦ điều kiện" if state["is_eligible_for_review"] else "CHƯA ĐỦ điều kiện"

    mandatory_missing_text = (
        "\n".join(f"  - {d}" for d in state["missing_mandatory_documents"])
        if state["missing_mandatory_documents"] else "  (Không có)"
    )
    optional_missing_text = (
        "\n".join(f"  - {d}" for d in state["missing_optional_documents"])
        if state["missing_optional_documents"] else "  (Không có)"
    )
    invalid_text = (
        "\n".join(f"  - {f}" for f in state["invalid_docs"])
        if state["invalid_docs"] else "  (Không có)"
    )

    # Nếu đang được resume sau khi bị REJECT, đưa feedback của user vào prompt
    # để LLM sinh lại nội dung tốt hơn.
    feedback_text = ""
    if state.get("human_feedback") and not state["human_feedback"].get("approve", True):
        fb = state["human_feedback"].get("feedback")
        if fb:
            feedback_text = f"\n\nLƯU Ý: Lần trước cán bộ thẩm định đã từ chối bản nháp với góp ý sau, hãy điều chỉnh cho phù hợp:\n{fb}\n"

    prompt = f"""
Bạn là chuyên gia thẩm định hồ sơ tín dụng tại một ngân hàng Việt Nam.

THÔNG TIN HỒ SƠ:
- Loại sản phẩm vay: {state["loan_profile_type"]}
- Trạng thái: {eligible} thẩm định
- Mức độ rủi ro: {state["risk_level"]}
- Tỷ lệ hoàn thiện (bắt buộc): {stats["completion_rate"]}%
- Chứng từ hợp lệ: {stats["total_valid"]} | Không hợp lệ: {stats["total_invalid"]}
- Còn thiếu bắt buộc: {stats["total_mandatory_missing"]} | Thiếu tùy chọn: {stats["total_optional_missing"]}

NHẬN XÉT TỪ AGENT A:
{state["analysis"]}

CHỨNG TỪ BẮT BUỘC CÒN THIẾU:
{mandatory_missing_text}

CHỨNG TỪ TÙY CHỌN CÒN THIẾU:
{optional_missing_text}

CHỨNG TỪ KHÔNG HỢP LỆ:
{invalid_text}
{feedback_text}
Trả về JSON theo đúng cấu trúc sau, KHÔNG thêm bất kỳ text nào ngoài JSON:
{{
    "overall_assessment": "Đánh giá tổng thể 2-3 câu về chất lượng hồ sơ, đề cập loại sản phẩm vay",
    "warning_report": "Cảnh báo chi tiết: rủi ro pháp lý, rủi ro tín dụng, lý do chưa đủ điều kiện (nếu có)",
    "missing_mandatory_vi": ["Tên tiếng Việt đầy đủ của từng chứng từ BẮT BUỘC còn thiếu"],
    "missing_optional_vi": ["Tên tiếng Việt đầy đủ của từng chứng từ TÙY CHỌN còn thiếu"],
    "recommendations": ["Hành động cụ thể cán bộ thẩm định cần thực hiện, ưu tiên chứng từ bắt buộc trước"]
}}

Lưu ý:
- Dịch mã chứng từ (snake_case) sang tên tiếng Việt đầy đủ, đúng nghiệp vụ ngân hàng.
- Phân biệt rõ chứng từ bắt buộc và tùy chọn trong recommendations.
- Nếu risk_level = HIGH, warning_report phải nêu rõ lý do và hậu quả nếu tiếp tục thẩm định.
- Recommendations phải cụ thể theo nghiệp vụ ngân hàng Việt Nam và loại sản phẩm vay.
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    raw_text = response.choices[0].message.content.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    llm_output = json.loads(raw_text)

    usage       = response.usage
    input_cost  = usage.prompt_tokens     * GROQ_INPUT_COST_PER_1M  / 1_000_000
    output_cost = usage.completion_tokens * GROQ_OUTPUT_COST_PER_1M / 1_000_000
    print(f"[risk_assessor] Model: {GROQ_MODEL}")
    print(f"[risk_assessor] Tokens: {usage.prompt_tokens} in / {usage.completion_tokens} out")
    print(f"[risk_assessor] Chi phí: ${input_cost + output_cost:.6f} USD")

    return {**state, "llm_output": llm_output}


# ══════════════════════════════════════════════════════════════════════════════
# NODE 3.5 — human_approval  🧍 HUMAN-IN-THE-LOOP (interrupt)
# Dừng graph, chờ cán bộ thẩm định xác nhận/sửa nội dung LLM sinh ra
# ══════════════════════════════════════════════════════════════════════════════

def human_approval(state: GraphState) -> GraphState:
    decision = interrupt({
        "message": (
            "Vui lòng xem lại nội dung đánh giá rủi ro do LLM sinh ra. "
            "Gọi API resume với {'approve': true} để tiếp tục, "
            "hoặc {'approve': false, 'feedback': '...'} để yêu cầu sinh lại."
        ),
        "llm_output": state["llm_output"],
        "risk_level": state["risk_level"],
    })

    # decision là dict được gửi lên từ endpoint resume, dạng ApprovalDecision
    if decision.get("edited_llm_output"):
        # User tự sửa tay nội dung -> dùng luôn bản đã sửa
        return {**state, "llm_output": decision["edited_llm_output"], "human_feedback": decision}

    return {**state, "human_feedback": decision}


def _route_after_approval(state: GraphState) -> str:
    """Nếu user reject (và không sửa tay) -> quay lại risk_assessor sinh lại bản mới.
    Nếu approve (hoặc reject nhưng đã tự sửa tay) -> đi tiếp report_generator."""
    fb = state.get("human_feedback") or {}
    if fb.get("approve") is False and not fb.get("edited_llm_output"):
        return "risk_assessor"
    return "report_generator"


# ══════════════════════════════════════════════════════════════════════════════
# NODE 4 — report_generator
# ══════════════════════════════════════════════════════════════════════════════

def report_generator(state: GraphState) -> GraphState:
    llm = state["llm_output"]
    return {
        **state,
        "overall_assessment": llm.get("overall_assessment", ""),
        "warning_report": llm.get("warning_report", ""),
        "missing_mandatory_vi": llm.get("missing_mandatory_vi", []),
        "missing_optional_vi": llm.get("missing_optional_vi", []),
        "recommendations": llm.get("recommendations", []),
    }


# ══════════════════════════════════════════════════════════════════════════════
# NODE 5 — output_formatter
# ══════════════════════════════════════════════════════════════════════════════

def output_formatter(state: GraphState) -> GraphState:
    matched_summary = []
    for group, items in state["docs_by_group"].items():
        matched_summary.append(f"[{group}]")
        for item in items:
            matched_summary.append(f"  ✓ {item}")
    return {**state, "matched_summary": matched_summary}


# ══════════════════════════════════════════════════════════════════════════════
# BUILD GRAPH — thêm node human_approval + checkpointer (MemorySaver)
# ══════════════════════════════════════════════════════════════════════════════

_memory_saver = MemorySaver()


def _build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("input_parser",      input_parser)
    graph.add_node("document_analyzer", document_analyzer)
    graph.add_node("risk_assessor",     risk_assessor)
    graph.add_node("human_approval",    human_approval)
    graph.add_node("report_generator",  report_generator)
    graph.add_node("output_formatter",  output_formatter)

    graph.set_entry_point("input_parser")
    graph.add_edge("input_parser",      "document_analyzer")
    graph.add_edge("document_analyzer", "risk_assessor")
    graph.add_edge("risk_assessor",     "human_approval")
    graph.add_conditional_edges(
        "human_approval",
        _route_after_approval,
        {"risk_assessor": "risk_assessor", "report_generator": "report_generator"},
    )
    graph.add_edge("report_generator", "output_formatter")
    graph.add_edge("output_formatter", END)

    # checkpointer bắt buộc phải có để interrupt() hoạt động (lưu state giữa các lần gọi API)
    return graph.compile(checkpointer=_memory_saver)


_agent_graph = _build_graph()


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _state_to_output(final_state: dict) -> AgentBOutput:
    return AgentBOutput(
        loan_profile_type=final_state["loan_profile_type"],
        is_eligible_for_review=final_state["is_eligible_for_review"],
        overall_assessment=final_state["overall_assessment"],
        warning_report=final_state["warning_report"],
        missing_mandatory_documents=final_state["missing_mandatory_vi"],
        missing_optional_documents=final_state["missing_optional_vi"],
        matched_summary=final_state["matched_summary"],
        invalid_documents=final_state["invalid_docs"],
        recommendations=final_state["recommendations"],
    )


def _build_agent_a_failure_report(input_data: AgentAOutput) -> AgentBOutput:
    """Sinh report chuẩn khi Agent A không xử lý được hồ sơ
    (success=False hoặc thiếu validation_results). Trường hợp này KHÔNG
    cần qua human_approval vì không có nội dung LLM nào cần duyệt."""
    reason = input_data.error or "Không rõ nguyên nhân (Agent A không trả về chi tiết lỗi)."

    return AgentBOutput(
        loan_profile_type=input_data.loan_profile_type or "Không xác định",
        is_eligible_for_review=False,
        overall_assessment=(
            "Không thể thẩm định hồ sơ vì bước phân loại & đối chiếu checklist (Agent A) "
            "gặp lỗi trong quá trình xử lý."
        ),
        warning_report=(
            f"Agent A báo lỗi: {reason}. Cần kiểm tra lại chất lượng/định dạng chứng từ đầu vào "
            "(ảnh mờ, PDF hỏng, sai định dạng...) hoặc tình trạng dịch vụ Agent A trước khi tiếp tục thẩm định."
        ),
        missing_mandatory_documents=[],
        missing_optional_documents=[],
        matched_summary=[],
        invalid_documents=[],
        recommendations=[
            "Yêu cầu kiểm tra lại chất lượng file ảnh, PDF đã tải lên.",
            "Thử chạy lại thẩm định sau khi khắc phục.",
            "Nếu lỗi lặp lại nhiều lần, báo đội kỹ thuật kiểm tra dịch vụ Agent A.",
        ],
    )


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINTS — gọi từ main.py
# ══════════════════════════════════════════════════════════════════════════════

def start_agent_b(input_data: AgentAOutput, thread_id: Optional[str] = None) -> dict:
    """
    Bắt đầu 1 phiên chạy Agent B mới.
    Trả về dict:
      {"status": "completed", "result": AgentBOutput}          — khi Agent A lỗi (bỏ qua approval)
      {"status": "pending_approval", "thread_id": ..., "llm_output": ...}  — khi cần user duyệt
    """
    # Guard: Agent A báo lỗi hoặc thiếu dữ liệu -> trả report degrade ngay, không cần approve
    if not input_data.success or input_data.validation_results is None:
        return {"status": "completed", "result": _build_agent_a_failure_report(input_data)}

    vr = input_data.validation_results
    thread_id = thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: GraphState = {
        "loan_profile_type":           input_data.loan_profile_type,
        "analysis":                    vr.analysis,
        "matched_documents":           vr.matched_documents,
        "missing_mandatory_documents": vr.missing_mandatory_documents,
        "missing_optional_documents":  vr.missing_optional_documents,
        "is_eligible_for_review":      vr.is_eligible_for_review,
        "valid_docs": [], "invalid_docs": [], "docs_by_group": {},
        "doc_stats": {}, "risk_level": "",
        "llm_output": {}, "human_feedback": None,
        "overall_assessment": "", "warning_report": "",
        "missing_mandatory_vi": [], "missing_optional_vi": [],
        "matched_summary": [], "recommendations": [],
    }

    result_state = _agent_graph.invoke(initial_state, config=config)

    if "__interrupt__" in result_state:
        interrupt_payload = result_state["__interrupt__"][0].value
        return {
            "status": "pending_approval",
            "thread_id": thread_id,
            "llm_output": interrupt_payload["llm_output"],
        }

    return {"status": "completed", "result": _state_to_output(result_state)}


def resume_agent_b(thread_id: str, decision: dict) -> dict:
    """
    Resume phiên đang chờ approve.
    decision: {"approve": bool, "edited_llm_output": Optional[dict], "feedback": Optional[str]}
    """
    config = {"configurable": {"thread_id": thread_id}}

    result_state = _agent_graph.invoke(Command(resume=decision), config=config)

    if "__interrupt__" in result_state:
        # Trường hợp reject -> risk_assessor chạy lại -> lại dừng ở human_approval lần nữa
        interrupt_payload = result_state["__interrupt__"][0].value
        return {
            "status": "pending_approval",
            "thread_id": thread_id,
            "llm_output": interrupt_payload["llm_output"],
        }

    return {"status": "completed", "result": _state_to_output(result_state)}