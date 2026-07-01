import json
import requests
import gradio as gr

API_BASE = "http://localhost:8001"


# ── Helpers gọi API ────────────────────────────────────────────────────────────

def _extract(resp: dict):
    """Chuẩn hoá response từ API (pending_approval / completed) thành các phần hiển thị."""
    status = resp.get("status")
    if status == "pending_approval":
        return status, resp["thread_id"], resp["llm_output"], None
    elif status == "completed":
        return status, None, None, resp["result"]
    return status, None, None, None


def start_analysis(source: str, mock_choice: bool, json_input: str, folder_path: str):
    try:
        if mock_choice:
            resp = requests.post(f"{API_BASE}/analyze/mock", timeout=120).json()
        elif source == "folder_path":
            resp = requests.post(
                f"{API_BASE}/analyze/from-folder",
                json={"folder_path": folder_path}, timeout=120
            ).json()
        else:
            payload = json.loads(json_input)
            resp = requests.post(f"{API_BASE}/analyze", json=payload, timeout=120).json()
    except Exception as e:
        return (
            gr.update(visible=False), gr.update(visible=False),
            f"❌ Lỗi gọi API: {e}", None, "", "", "", "", ""
        )

    status, thread_id, llm_output, result = _extract(resp)

    if status == "pending_approval":
        return (
            gr.update(visible=True),                     # review_panel
            gr.update(visible=False),                    # result_panel
            "🟡 Đang chờ cán bộ thẩm định duyệt nội dung", # status_box
            thread_id,                                     # thread_id_state
            llm_output.get("overall_assessment", ""),
            llm_output.get("warning_report", ""),
            "\n".join(llm_output.get("missing_mandatory_vi", [])),
            "\n".join(llm_output.get("missing_optional_vi", [])),
            "\n".join(llm_output.get("recommendations", [])),
        )
    elif status == "completed":
        # Trường hợp Agent A lỗi -> bỏ qua approval, trả report degrade luôn
        md = _format_result_md(result)
        return (
            gr.update(visible=False),
            gr.update(visible=True),
            "✅ Hoàn tất (không cần duyệt — có thể do Agent A báo lỗi)",
            None,
            "", "", "", "", md,
        )
    else:
        return (
            gr.update(visible=False), gr.update(visible=False),
            f"❌ Lỗi không xác định: {resp}", None, "", "", "", "", ""
        )


def submit_decision(thread_id, approve: bool, overall, warning, mandatory, optional, recs, feedback):
    edited = None
    if approve:
        # Cho phép user sửa tay trước khi approve
        edited = {
            "overall_assessment": overall,
            "warning_report": warning,
            "missing_mandatory_vi": [x for x in mandatory.split("\n") if x.strip()],
            "missing_optional_vi": [x for x in optional.split("\n") if x.strip()],
            "recommendations": [x for x in recs.split("\n") if x.strip()],
        }

    body = {"approve": approve, "edited_llm_output": edited, "feedback": feedback or None}

    try:
        resp = requests.post(f"{API_BASE}/analyze/{thread_id}/resume", json=body, timeout=120).json()
    except Exception as e:
        return gr.update(visible=True), gr.update(visible=False), f"❌ Lỗi: {e}", thread_id, "", "", "", "", ""

    status, new_thread_id, llm_output, result = _extract(resp)

    if status == "pending_approval":
        # Bị reject -> LLM sinh lại -> hiển thị bản mới để duyệt tiếp
        return (
            gr.update(visible=True), gr.update(visible=False),
            "🟡 LLM đã sinh lại nội dung — vui lòng duyệt tiếp",
            new_thread_id,
            llm_output.get("overall_assessment", ""),
            llm_output.get("warning_report", ""),
            "\n".join(llm_output.get("missing_mandatory_vi", [])),
            "\n".join(llm_output.get("missing_optional_vi", [])),
            "\n".join(llm_output.get("recommendations", [])),
        )
    elif status == "completed":
        md = _format_result_md(result)
        return (
            gr.update(visible=False), gr.update(visible=True),
            "✅ Report đã được duyệt và hoàn tất",
            None, "", "", "", "", md,
        )
    else:
        return gr.update(visible=True), gr.update(visible=False), f"❌ Lỗi: {resp}", thread_id, "", "", "", "", ""


def _format_result_md(result: dict) -> str:
    lines = [
        f"## 📋 Report Thẩm Định — {result['loan_profile_type']}",
        f"**Đủ điều kiện thẩm định:** {'✅ Có' if result['is_eligible_for_review'] else '❌ Chưa'}",
        "### Đánh giá tổng thể",
        result["overall_assessment"],
        "### ⚠️ Cảnh báo",
        result["warning_report"],
        "### 📄 Chứng từ bắt buộc còn thiếu",
        "\n".join(f"- {x}" for x in result["missing_mandatory_documents"]) or "_Không có_",
        "### 📄 Chứng từ tùy chọn còn thiếu",
        "\n".join(f"- {x}" for x in result["missing_optional_documents"]) or "_Không có_",
        "### ✅ Chứng từ hợp lệ",
        "\n".join(result["matched_summary"]) or "_Không có_",
        "### 🚫 Chứng từ không hợp lệ",
        "\n".join(f"- {x}" for x in result["invalid_documents"]) or "_Không có_",
        "### 👉 Đề xuất hành động",
        "\n".join(f"- {x}" for x in result["recommendations"]),
    ]
    return "\n\n".join(lines)


# ── UI Layout ──────────────────────────────────────────────────────────────────

with gr.Blocks(title="Agent B – Thẩm Định Hồ Sơ Tín Dụng") as demo:
    gr.Markdown("# 🏦 Agent B – Report Thẩm Định Hồ Sơ Tín Dụng")

    thread_id_state = gr.State(None)

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 1️⃣ Nguồn dữ liệu")
            mock_checkbox = gr.Checkbox(label="Dùng mock data (test nhanh, không cần Agent A)", value=True)
            source_radio = gr.Radio(
                ["folder_path", "json_agent_a"], value="folder_path",
                label="Nguồn dữ liệu (khi không dùng mock)"
            )
            folder_input = gr.Textbox(label="Đường dẫn thư mục hồ sơ", placeholder="D:/2026RA/input_profiles_test")
            json_input = gr.Textbox(label="JSON output từ Agent A", lines=8, placeholder='{"success": true, ...}')
            run_btn = gr.Button("🚀 Phân tích", variant="primary")

        with gr.Column(scale=1):
            status_box = gr.Markdown("Chưa chạy phân tích")

    with gr.Group(visible=False) as review_panel:
        gr.Markdown("### 2️⃣ Xem lại nội dung LLM sinh ra & Duyệt")
        overall_box   = gr.Textbox(label="Đánh giá tổng thể", lines=2)
        warning_box   = gr.Textbox(label="Cảnh báo chi tiết", lines=4)
        mandatory_box = gr.Textbox(label="Chứng từ bắt buộc thiếu (mỗi dòng 1 mục)", lines=4)
        optional_box  = gr.Textbox(label="Chứng từ tùy chọn thiếu (mỗi dòng 1 mục)", lines=3)
        recs_box      = gr.Textbox(label="Đề xuất hành động (mỗi dòng 1 mục)", lines=4)
        feedback_box  = gr.Textbox(label="Feedback (chỉ cần khi Reject)", placeholder="Cần nêu rõ hơn rủi ro pháp lý...")

        with gr.Row():
            approve_btn = gr.Button("✅ Approve", variant="primary")
            reject_btn  = gr.Button("❌ Reject (sinh lại)", variant="stop")

    result_panel = gr.Markdown(visible=False)

    run_btn.click(
        start_analysis,
        inputs=[source_radio, mock_checkbox, json_input, folder_input],
        outputs=[review_panel, result_panel, status_box, thread_id_state,
                 overall_box, warning_box, mandatory_box, optional_box, recs_box],
    )

    approve_btn.click(
        lambda tid, o, w, m, opt, r, fb: submit_decision(tid, True, o, w, m, opt, r, fb),
        inputs=[thread_id_state, overall_box, warning_box, mandatory_box, optional_box, recs_box, feedback_box],
        outputs=[review_panel, result_panel, status_box, thread_id_state,
                 overall_box, warning_box, mandatory_box, optional_box, recs_box],
    )

    reject_btn.click(
        lambda tid, o, w, m, opt, r, fb: submit_decision(tid, False, o, w, m, opt, r, fb),
        inputs=[thread_id_state, overall_box, warning_box, mandatory_box, optional_box, recs_box, feedback_box],
        outputs=[review_panel, result_panel, status_box, thread_id_state,
                 overall_box, warning_box, mandatory_box, optional_box, recs_box],
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)