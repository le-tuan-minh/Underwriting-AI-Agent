# Agent B – Report Thẩm Định Hồ Sơ Tín Dụng

Agent B nhận output từ Agent A (phân loại & đối chiếu checklist hồ sơ vay), sau đó sinh báo cáo cảnh báo chất lượng, liệt kê chứng từ còn thiếu và đề xuất hành động cho cán bộ thẩm định.

---

## Kiến trúc

```
Agent A (phân loại hồ sơ)
        ↓  AgentAOutput (JSON)
Agent B (LangGraph pipeline)
   ├── input_parser       — chuẩn hóa dữ liệu đầu vào
   ├── document_analyzer  — tính thống kê, xác định mức rủi ro
   ├── risk_assessor      — gọi LLM sinh cảnh báo & khuyến nghị
   ├── report_generator   — tổng hợp output từ LLM
   └── output_formatter   — format matched docs theo nhóm
        ↓  AgentBOutput (JSON)
FastAPI endpoint
```

**LLM:** Groq (`llama-3.3-70b-versatile`) — thay bằng Claude Sonnet khi tích hợp chính thức.

---

## Cài đặt

```bash
pip install -r requirements.txt
```

Tạo file `.env`:
```env
GROQ_API_KEY=your_groq_api_key
AGENT_A_URL=http://localhost:8000/api/v1/validate-profile
AGENT_A_TIMEOUT=120
```

Chạy server:
```bash
uvicorn app_groq.main:app --host 0.0.0.0 --port 8001 --reload
```

---

## API Endpoints

| Method | Path | Mô tả |
|--------|------|-------|
| `GET` | `/` | Health check |
| `POST` | `/analyze/from-folder` | Luồng chính: nhận `folder_path`, tự gọi Agent A rồi sinh report |
| `POST` | `/analyze` | Nhận trực tiếp `AgentAOutput` (server-to-server) |
| `POST` | `/analyze/mock` | Test Agent B với mock data, không cần Agent A |

### Ví dụ — luồng chính

```bash
curl -X POST http://localhost:8001/analyze/from-folder \
  -H "Content-Type: application/json" \
  -d '{"folder_path": "D:/2026RA/input_profiles_test"}'
```

### Ví dụ — test với mock data

```bash
curl -X POST http://localhost:8001/analyze/mock
```

---

## Output mẫu (`AgentBOutput`)

```json
{
  "loan_profile_type": "Vay thế chấp bất động sản",
  "is_eligible_for_review": false,
  "overall_assessment": "Hồ sơ còn thiếu 4 chứng từ bắt buộc, mức rủi ro HIGH...",
  "warning_report": "Thiếu sổ đỏ, chứng thư định giá...",
  "missing_mandatory_documents": ["Hợp đồng đặt cọc nhà", "Sổ đỏ", "..."],
  "missing_optional_documents": ["Tình trạng hôn nhân", "..."],
  "matched_summary": ["[1_Pháp lý nhân thân]", "  ✓ 01_cccd_front.png (CCCD...)", "..."],
  "invalid_documents": [],
  "recommendations": ["Yêu cầu khách hàng bổ sung ngay...", "..."]
}
```

---

## Cấu trúc thư mục

```
app_groq/
├── main.py           — FastAPI app & endpoints
├── agent_b.py        — LangGraph pipeline (5 nodes)
├── agent_a_client.py — HTTP client gọi Agent A
├── schemas.py        — Pydantic schemas (input/output)
└── mock_data.py      — Mock AgentAOutput để test độc lập
requirements.txt
.env                  — (không commit, xem .gitignore)
```

---

## Mức rủi ro

| Mức | Điều kiện |
|-----|-----------|
| `HIGH` | `is_eligible_for_review = False` hoặc tỷ lệ hoàn thiện < 50% |
| `MEDIUM` | Tỷ lệ hoàn thiện < 75%, hoặc có chứng từ không hợp lệ / thiếu bắt buộc |
| `LOW` | Đủ điều kiện, tỷ lệ hoàn thiện ≥ 75%, không có lỗi |