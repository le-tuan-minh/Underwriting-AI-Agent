import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from app_groq.schemas import AgentAOutput, AgentBOutput
from app_groq.agent_b import run_agent_b
from app_groq.agent_a_client import call_agent_a, AgentAError
from app_groq.mock_data import MOCK_INPUT

load_dotenv()

app = FastAPI(
    title="Agent B – Report Thẩm Định Hồ Sơ",
    description=(
        "Nhận output từ Agent A (phân loại & đối chiếu checklist), "
        "sinh report cảnh báo chất lượng, chứng từ thiếu, và đề xuất hành động."
    ),
    version="3.1.0",
)


# ── Request schemas ───────────────────────────────────────────────────────────

class FolderRequest(BaseModel):
    folder_path: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {
        "message": "Agent B đang chạy",
        "version": "3.1.0",
        "agent_a_url": os.getenv("AGENT_A_URL", "http://localhost:8000/api/v1/validate-profile"),
    }


@app.post("/analyze/from-folder", response_model=AgentBOutput, tags=["Agent B"])
def analyze_from_folder(request: FolderRequest):
    """
    **Luồng chính**: Nhận đường dẫn thư mục hồ sơ,
    tự động gọi Agent A để phân loại → Agent B sinh report.

    Body:
    ```json
    { "folder_path": "D:/2026RA/input_profiles_test" }
    ```
    """
    # Bước 1: Gọi Agent A
    try:
        agent_a_output = call_agent_a(request.folder_path)
    except AgentAError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Lỗi không xác định khi gọi Agent A: {str(e)}"
        )

    # Bước 2: Chạy Agent B
    try:
        return run_agent_b(agent_a_output)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent B lỗi: {str(e)}")


@app.post("/analyze", response_model=AgentBOutput, tags=["Agent B"])
def analyze(input_data: AgentAOutput):
    """
    Nhận trực tiếp output của Agent A (dùng khi tích hợp server-to-server).
    Body theo schema AgentAOutput.
    """
    if not input_data.success:
        raise HTTPException(
            status_code=422,
            detail=f"Agent A báo lỗi: {input_data.error or 'Không rõ nguyên nhân'}"
        )
    try:
        return run_agent_b(input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/mock", response_model=AgentBOutput, tags=["Agent B"])
def analyze_mock():
    """
    Chạy Agent B với mock data (không cần Agent A chạy).
    Dùng để test độc lập Agent B.
    """
    try:
        return run_agent_b(MOCK_INPUT)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))