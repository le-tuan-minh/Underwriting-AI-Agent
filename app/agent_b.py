import os
from anthropic import Anthropic
from dotenv import load_dotenv
from app.schemas import AgentAOutput, AgentBOutput

load_dotenv()
client = Anthropic()

def run_agent_b(input_data: AgentAOutput) -> AgentBOutput:

    # Chuẩn bị thông tin checklist để đưa vào prompt
    checklist_text = "\n".join([
        f"- {item}: {'Đạt' if passed else 'KHÔNG ĐẠT'}"
        for item, passed in input_data.checklist.items()
    ])

    prompt = f"""
Bạn là chuyên gia thẩm định hồ sơ ngân hàng.
Dưới đây là kết quả phân tích một văn bản từ hồ sơ khách hàng:

Mã hồ sơ: {input_data.document_id}
Loại văn bản: {input_data.document_type}
Tóm tắt nội dung: {input_data.summary}

Kết quả kiểm tra checklist:
{checklist_text}

Hãy tạo report theo đúng format JSON sau, không thêm bất kỳ text nào khác:
{{
    "report": "Nội dung cảnh báo chi tiết",
    "missing_documents": ["chứng từ 1", "chứng từ 2"],
    "error_pages": ["mô tả lỗi 1", "mô tả lỗi 2"]
}}
"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse kết quả JSON từ Claude
    import json
    raw_text = message.content[0].text
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    result = json.loads(raw_text.strip())

    # Tính token và chi phí (giá Claude Sonnet 4.6)
    input_tokens = message.usage.input_tokens
    output_tokens = message.usage.output_tokens
    input_cost = input_tokens * 3 / 1_000_000      # $3 per 1M input tokens
    output_cost = output_tokens * 15 / 1_000_000   # $15 per 1M output tokens
    total_cost = input_cost + output_cost

    print(f"Input tokens:  {input_tokens}")
    print(f"Output tokens: {output_tokens}")
    print(f"Chi phí:       ${total_cost:.6f} USD")

    return AgentBOutput(
        document_id=input_data.document_id,
        report=result["report"],
        missing_documents=result["missing_documents"],
        error_pages=result["error_pages"]
    )