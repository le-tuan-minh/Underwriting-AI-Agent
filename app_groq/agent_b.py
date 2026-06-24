import os
import json
from typing import TypedDict, List
from groq import Groq
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from app_groq.schemas import AgentAOutput, AgentBOutput, MatchedDocument

load_dotenv()

# ── Groq client ───────────────────────────────────────────────────────────────
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

GROQ_MODEL              = "llama-3.3-70b-versatile"
GROQ_INPUT_COST_PER_1M  = 0.59
GROQ_OUTPUT_COST_PER_1M = 0.79


# ── GraphState ────────────────────────────────────────────────────────────────

class GraphState(TypedDict):
    # Input từ Agent A
    analysis: str
    matched_documents: List[MatchedDocument]
    missing_documents: List[str]
    is_eligible_for_review: bool

    # Trung gian — do các node tính toán
    valid_docs: List[str]           # file_assigned của doc có status Valid
    invalid_docs: List[str]         # file_assigned của doc có status Invalid
    doc_stats: dict                 # tổng hợp số liệu hồ sơ
    risk_level: str                 # "LOW" / "MEDIUM" / "HIGH"

    # Raw output từ LLM
    llm_output: dict

    # Output cuối
    overall_assessment: str
    warning_report: str
    missing_documents_vi: List[str]
    matched_summary: List[str]
    recommendations: List[str]


# ══════════════════════════════════════════════════════════════════════════════
# NODE 1 — input_parser
# Validate và chuẩn hóa dữ liệu từ Agent A vào GraphState
# ══════════════════════════════════════════════════════════════════════════════

def input_parser(state: GraphState) -> GraphState:
    valid_docs   = [d.file_assigned for d in state["matched_documents"] if d.status == "Valid"]
    invalid_docs = [d.file_assigned for d in state["matched_documents"] if d.status != "Valid"]

    return {
        **state,
        "valid_docs":   valid_docs,
        "invalid_docs": invalid_docs,
    }


# ══════════════════════════════════════════════════════════════════════════════
# NODE 2 — document_analyzer
# Tính thống kê hồ sơ và xác định mức độ rủi ro — không gọi LLM
# ══════════════════════════════════════════════════════════════════════════════

# Mapping mã chứng từ → nhóm nghiệp vụ
_DOC_GROUP_MAP = {
    "Giay_dang_ky_ket_hon":            "Nhân thân",
    "Bao_cao_tai_chinh_BCTC":          "Tài chính",
    "Giay_to_ton_tai_GCN_HDMB":        "Tài sản bảo đảm",
    "Hop_dong_cho_thue":               "Tài chính",
    "Chung_tu_nhan_tien_thue":         "Tài chính",
    "Anh_cho_thue":                    "Tài chính",
    "Hop_dong_tin_dung_HDTD":          "Pháp lý tín dụng",
    "Hop_dong_dat_coc_nha":            "Tài sản bảo đảm",
    "GCN_QSDĐ":                        "Tài sản bảo đảm",
    "Giay_to_phap_ly_TSBD_GCN_QSDĐ":  "Tài sản bảo đảm",
    "Chung_thu_dinh_gia":              "Tài sản bảo đảm",
    "Bao_cao_de_xuat_cap_tin_dung":    "Pháp lý tín dụng",
}

def document_analyzer(state: GraphState) -> GraphState:
    total_matched  = len(state["matched_documents"])
    total_valid    = len(state["valid_docs"])
    total_invalid  = len(state["invalid_docs"])
    total_missing  = len(state["missing_documents"])
    total_required = total_matched + total_missing

    completion_rate = round(total_valid / total_required * 100, 1) if total_required > 0 else 0.0

    # Nhóm các chứng từ thiếu theo nghiệp vụ
    missing_by_group: dict[str, list] = {}
    for doc in state["missing_documents"]:
        group = _DOC_GROUP_MAP.get(doc, "Khác")
        missing_by_group.setdefault(group, []).append(doc)

    doc_stats = {
        "total_matched":   total_matched,
        "total_valid":     total_valid,
        "total_invalid":   total_invalid,
        "total_missing":   total_missing,
        "completion_rate": completion_rate,
        "missing_by_group": missing_by_group,
    }

    # Xác định mức rủi ro dựa trên tỷ lệ hoàn thiện và is_eligible
    if not state["is_eligible_for_review"] or completion_rate < 50:
        risk_level = "HIGH"
    elif completion_rate < 75 or total_invalid > 0:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {**state, "doc_stats": doc_stats, "risk_level": risk_level}


# ══════════════════════════════════════════════════════════════════════════════
# NODE 3 — risk_assessor  ⚡ LLM call duy nhất
# Gọi Groq để sinh warning_report, missing_documents_vi, recommendations
# ══════════════════════════════════════════════════════════════════════════════

def risk_assessor(state: GraphState) -> GraphState:
    stats    = state["doc_stats"]
    eligible = "ĐỦ điều kiện" if state["is_eligible_for_review"] else "CHƯA ĐỦ điều kiện"

    # Chuẩn bị danh sách thiếu theo nhóm
    missing_group_text = "\n".join(
        f"  [{group}]: {', '.join(docs)}"
        for group, docs in stats["missing_by_group"].items()
    )

    # Chứng từ invalid (nếu có)
    invalid_text = (
        "\n".join(f"  - {f}" for f in state["invalid_docs"])
        if state["invalid_docs"] else "  (Không có)"
    )

    prompt = f"""
Bạn là chuyên gia thẩm định hồ sơ tín dụng tại một ngân hàng Việt Nam.

THÔNG TIN HỒ SƠ:
- Trạng thái: {eligible} thẩm định
- Mức độ rủi ro: {state["risk_level"]}
- Tỷ lệ hoàn thiện: {stats["completion_rate"]}%
- Chứng từ hợp lệ: {stats["total_valid"]} | Không hợp lệ: {stats["total_invalid"]} | Còn thiếu: {stats["total_missing"]}

NHẬN XÉT TỪ HỆ THỐNG TRƯỚC:
{state["analysis"]}

CHỨNG TỪ CÒN THIẾU (theo nhóm):
{missing_group_text}

CHỨNG TỪ KHÔNG HỢP LỆ:
{invalid_text}

Trả về JSON theo đúng cấu trúc sau, KHÔNG thêm bất kỳ text nào ngoài JSON:
{{
    "overall_assessment": "Đánh giá tổng thể 2-3 câu về chất lượng hồ sơ",
    "warning_report": "Cảnh báo chi tiết: rủi ro pháp lý, rủi ro tín dụng, lý do chưa đủ điều kiện (nếu có)",
    "missing_documents_vi": ["Tên tiếng Việt đầy đủ của từng chứng từ còn thiếu"],
    "recommendations": ["Hành động cụ thể cán bộ thẩm định cần thực hiện"]
}}

Lưu ý:
- Dịch tên mã chứng từ sang tiếng Việt đầy đủ trong missing_documents_vi.
- Nếu risk_level = HIGH, warning_report phải nêu rõ lý do và hậu quả nếu tiếp tục thẩm định.
- Recommendations phải cụ thể theo nghiệp vụ ngân hàng Việt Nam.
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

    # Log chi phí
    usage         = response.usage
    input_cost    = usage.prompt_tokens     * GROQ_INPUT_COST_PER_1M  / 1_000_000
    output_cost   = usage.completion_tokens * GROQ_OUTPUT_COST_PER_1M / 1_000_000
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
        "missing_documents_vi": llm.get("missing_documents_vi", []),
        "recommendations":     llm.get("recommendations", []),
    }


# ══════════════════════════════════════════════════════════════════════════════
# NODE 5 — output_formatter
# Map GraphState → AgentBOutput schema — không gọi LLM
# ══════════════════════════════════════════════════════════════════════════════

def output_formatter(state: GraphState) -> GraphState:
    matched_summary = [
        f"{d.file_assigned} [{d.checklist_item}] - {'Hợp lệ' if d.status == 'Valid' else d.status}"
        for d in state["matched_documents"]
    ]

    return {
        **state,
        "matched_summary": matched_summary,
    }


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
# PUBLIC ENTRY POINT — gọi từ main.py (interface không đổi)
# ══════════════════════════════════════════════════════════════════════════════

def run_agent_b(input_data: AgentAOutput) -> AgentBOutput:
    initial_state: GraphState = {
        "analysis":             input_data.analysis,
        "matched_documents":    input_data.matched_documents,
        "missing_documents":    input_data.missing_documents,
        "is_eligible_for_review": input_data.is_eligible_for_review,
        # Các field trung gian — sẽ được điền bởi các node
        "valid_docs":           [],
        "invalid_docs":         [],
        "doc_stats":            {},
        "risk_level":           "",
        "llm_output":           {},
        "overall_assessment":   "",
        "warning_report":       "",
        "missing_documents_vi": [],
        "matched_summary":      [],
        "recommendations":      [],
    }

    final_state = _agent_graph.invoke(initial_state)

    return AgentBOutput(
        is_eligible_for_review=final_state["is_eligible_for_review"],
        overall_assessment=final_state["overall_assessment"],
        warning_report=final_state["warning_report"],
        missing_documents=final_state["missing_documents_vi"],
        matched_summary=final_state["matched_summary"],
        invalid_documents=final_state["invalid_docs"],
        recommendations=final_state["recommendations"],
    )