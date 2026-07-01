import os
import httpx
import pydantic
from app_groq.schemas import AgentAOutput

AGENT_A_URL = os.getenv("AGENT_A_URL", "http://localhost:8000/api/v1/validate-profile")
AGENT_A_TIMEOUT = float(os.getenv("AGENT_A_TIMEOUT", "120"))


class AgentAError(Exception):
    """Lỗi tầng kết nối/giao tiếp với Agent A: không tới được, timeout, HTTP lỗi, sai schema."""
    pass


def call_agent_a(folder_path: str) -> AgentAOutput:
    """
    Gửi POST tới Agent A. Lưu ý: nếu Agent A trả success=False (lỗi NGHIỆP VỤ,
    ví dụ không đọc được ảnh), hàm này KHÔNG raise mà trả nguyên AgentAOutput
    (kèm error message) để Agent B tự xử lý và sinh report degrade tương ứng.
    Chỉ raise AgentAError khi lỗi ở tầng KẾT NỐI/GIAO TIẾP.
    """
    payload = {"folder_path": folder_path}

    try:
        response = httpx.post(AGENT_A_URL, json=payload, timeout=AGENT_A_TIMEOUT)
        response.raise_for_status()
    except httpx.ConnectError:
        raise AgentAError(
            f"Không kết nối được tới Agent A tại {AGENT_A_URL}. "
            "Kiểm tra Agent A đang chạy và AGENT_A_URL trong .env."
        )
    except httpx.TimeoutException:
        raise AgentAError(
            f"Agent A không phản hồi sau {AGENT_A_TIMEOUT}s. "
            "Thử tăng AGENT_A_TIMEOUT trong .env."
        )
    except httpx.HTTPStatusError as e:
        raise AgentAError(
            f"Agent A trả HTTP {e.response.status_code}: {e.response.text[:300]}"
        )

    raw = response.json()

    try:
        return AgentAOutput(**raw)
    except pydantic.ValidationError as e:
        raise AgentAError(f"Agent A trả về dữ liệu không đúng định dạng mong đợi: {e}")