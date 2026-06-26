import os
import httpx
from app_groq.schemas import AgentAOutput

# Đọc từ env, fallback về localhost
AGENT_A_URL = os.getenv("AGENT_A_URL", "http://localhost:8000/api/v1/validate-profile")
AGENT_A_TIMEOUT = float(os.getenv("AGENT_A_TIMEOUT", "120"))  # giây


class AgentAError(Exception):
    """Raised khi Agent A trả lỗi hoặc không kết nối được."""
    pass


def call_agent_a(folder_path: str) -> AgentAOutput:
    """
    Gửi POST tới Agent A với folder_path,
    parse response thành AgentAOutput và trả về.

    Raises:
        AgentAError — nếu không kết nối được hoặc Agent A báo lỗi
        pydantic.ValidationError — nếu response không đúng schema
    """
    payload = {"folder_path": folder_path}

    try:
        response = httpx.post(
            AGENT_A_URL,
            json=payload,
            timeout=AGENT_A_TIMEOUT,
        )
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

    # Kiểm tra flag success từ Agent A
    if not raw.get("success", True):
        raise AgentAError(
            f"Agent A báo lỗi xử lý: {raw.get('error', 'Không rõ nguyên nhân')}"
        )

    return AgentAOutput(**raw)