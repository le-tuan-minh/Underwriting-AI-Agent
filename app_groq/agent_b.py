import os
import json
from typing import TypedDict, List, Dict
from groq import Groq
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from app_groq.schemas import AgentAOutput, AgentBOutput, MatchedDocument

load_dotenv()

# ── Groq client ────────────────────────────────────────────────────────────────
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

GROQ_MODEL              = "llama-3.3-70b-versatile"
GROQ_INPUT_COST_PER_1M  = 0.59   # USD per 1M input tokens
GROQ_OUTPUT_COST_PER_1M = 0.79   # USD per 1M output tokens


# ── GraphState ────────────────────────────────────────────────────────────────

class GraphState(TypedDict):
    # Input từ Agent A
    loan_profile_type: str
    analysis: str
    matched_documents: List[MatchedDocument]
    missing_mandatory_documents: List[str]
    missing_optional_documents: List[str]
    is_eligible_for_review: bool

    # Trung gian — do các node tính toán
    valid_docs: List[str]
    invalid_docs: List[str]
    docs_by_group: Dict[str, List[str]]     # matched docs nhóm theo group
    doc_stats: dict
    risk_level: str                          # "LOW" / "MEDIUM" / "HIGH"

    # Raw output từ LLM
    llm_output: dict

    # Output cuối
    overall_assessment: str
    warning_report: str
    missing_mandatory_vi: List[str]
    missing_optional_vi: List[str]
    matched_summary: List[str]
    recommendations: List[str]


# ══════════════════════════════════════════════════════════════════════════════
# NODE 1 — input_parser
# Validate và chuẩn hóa dữ liệu từ Agent A vào GraphState
# ══════════════════════════════════════════════════════════════════════════════

def input_parser(state: GraphState) -> GraphState:
    valid_docs   = [d.file_assigned for d in state["matched_documents"] if d.status == "Valid"]
    invalid_docs = [d.file_assigned for d in state["matched_documents"] if d.status != "Valid"]

    # Nhóm matched docs theo group
    docs_by_group: Dict[str, List[str]] = {}
    for d in state["matched_documents"]:
        docs_by_group.setdefault(d.group, []).append(
            f"{d.file_assigned} ({d.checklist_item})"
        )

    return {
        **state,
        "valid_docs":    valid_docs,
        "invalid_docs":  invalid_docs,
        "docs_by_group": docs_by_group,
    }


# ══════════════════════════════════════════════════════════════════════════════
# NODE 2 — document_analyzer
# Tính thống kê hồ sơ và xác định mức độ rủi ro — không gọi LLM
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
        "total_matched":          total_matched,
        "total_valid":            total_valid,
        "total_invalid":          total_invalid,
        "total_mandatory_missing": total_mandatory_missing,
        "total_optional_missing":  total_optional_missing,
        "completion_rate":        completion_rate,
    }

    # Xác định mức rủi ro
    if not state["is_eligible_for_review"] or completion_rate < 50:
        risk_level = "HIGH"
    elif completion_rate < 75 or total_invalid > 0 or total_mandatory_missing > 0:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {**state, "doc_stats": doc_stats, "risk_level": risk_level}


# ══════════════════════════════════════════════════════════════════════════════
# NODE 3 — risk_assessor  ⚡ LLM call duy nhất (Claude Sonnet)
# Gọi Anthropic để sinh warning_report, missing docs (VI), recommendations
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
    # Strip markdown fences nếu có
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    llm_output = json.loads(raw_text)

    # Log chi phí
    usage       = response.usage
    input_cost  = usage.prompt_tokens     * GROQ_INPUT_COST_PER_1M  / 1_000_000
    output_cost = usage.completion_tokens * GROQ_OUTPUT_COST_PER_1M / 1_000_000
    print(f"[risk_assessor] Model: {GROQ_MODEL}")
    print(f"[risk_assessor] Tokens: {usage.prompt_tokens} in / {usage.completion_tokens} out")
    print(f"[risk_assessor] Chi phí: ${input_cost + output_cost:.6f} USD")

    return {**state, "llm_output": llm_output}


# ══════════════════════════════════════════════════════════════════════════════
# NODE 4 — report_generator
# Đọc llm_output từ GraphState, tổng hợp report — không gọi LLM
# ══════════════════════════════════════════════════════════════════════════════

def report_generator(state: GraphState) -> GraphState:
    llm = state["llm_output"]

    return {
        **state,
        "overall_assessment":  llm.get("overall_assessment", ""),
        "warning_report":      llm.get("warning_report", ""),
        "missing_mandatory_vi": llm.get("missing_mandatory_vi", []),
        "missing_optional_vi":  llm.get("missing_optional_vi", []),
        "recommendations":     llm.get("recommendations", []),
    }


# ══════════════════════════════════════════════════════════════════════════════
# NODE 5 — output_formatter
# Map GraphState → AgentBOutput schema — không gọi LLM
# ══════════════════════════════════════════════════════════════════════════════

def output_formatter(state: GraphState) -> GraphState:
    matched_summary = []
    for group, items in state["docs_by_group"].items():
        matched_summary.append(f"[{group}]")
        for item in items:
            matched_summary.append(f"  ✓ {item}")

    return {**state, "matched_summary": matched_summary}


# ══════════════════════════════════════════════════════════════════════════════
# BUILD GRAPH
# ══════════════════════════════════════════════════════════════════════════════

def _build_graph() -> StateGraph:
    graph = StateGraph(GraphState)

    graph.add_node("input_parser",      input_parser)
    graph.add_node("document_analyzer", document_analyzer)
    graph.add_node("risk_assessor",     risk_assessor)
    graph.add_node("report_generator",  report_generator)
    graph.add_node("output_formatter",  output_formatter)

    graph.set_entry_point("input_parser")
    graph.add_edge("input_parser",      "document_analyzer")
    graph.add_edge("document_analyzer", "risk_assessor")
    graph.add_edge("risk_assessor",     "report_generator")
    graph.add_edge("report_generator",  "output_formatter")
    graph.add_edge("output_formatter",  END)

    return graph.compile()


_agent_graph = _build_graph()


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINT — gọi từ main.py
# ══════════════════════════════════════════════════════════════════════════════

def run_agent_b(input_data: AgentAOutput) -> AgentBOutput:
    vr = input_data.validation_results

    initial_state: GraphState = {
        "loan_profile_type":           input_data.loan_profile_type,
        "analysis":                    vr.analysis,
        "matched_documents":           vr.matched_documents,
        "missing_mandatory_documents": vr.missing_mandatory_documents,
        "missing_optional_documents":  vr.missing_optional_documents,
        "is_eligible_for_review":      vr.is_eligible_for_review,
        # Các field trung gian
        "valid_docs":          [],
        "invalid_docs":        [],
        "docs_by_group":       {},
        "doc_stats":           {},
        "risk_level":          "",
        "llm_output":          {},
        "overall_assessment":  "",
        "warning_report":      "",
        "missing_mandatory_vi": [],
        "missing_optional_vi":  [],
        "matched_summary":     [],
        "recommendations":     [],
    }

    final_state = _agent_graph.invoke(initial_state)

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