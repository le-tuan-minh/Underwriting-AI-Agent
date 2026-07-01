import os
from typing import Union
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from app_groq.schemas import (
    AgentAOutput, ApprovalDecision,
    PendingApprovalResponse, CompletedResponse,
)
from app_groq.agent_b import start_agent_b, resume_agent_b
from app_groq.agent_a_client import call_agent_a, AgentAError
from app_groq.mock_data import MOCK_INPUT

load_dotenv()

app = FastAPI(
    title="Agent B – Report Thẩm Định Hồ Sơ",
    description=(
        "Nhận output từ Agent A, sinh report cảnh báo chất lượng, chứng từ thiếu, "
        "đề xuất hành động — có bước xác nhận (human-in-the-loop) trước khi chốt report."
    ),
    version="4.0.0",
)


class FolderRequest(BaseModel):
    folder_path: str


ResumeResponse = Union[PendingApprovalResponse, CompletedResponse]
AnalyzeResponse = Union[PendingApprovalResponse, CompletedResponse]


@app.get("/", tags=["Health"])
def root():
    return {
        "message": "Agent B đang chạy",
        "version": "4.0.0",
        "agent_a_url": os.getenv("AGENT_A_URL", "http://localhost:8000/api/v1/validate-profile"),
    }


@app.post("/analyze/from-folder", response_model=AnalyzeResponse, tags=["Agent B"])
def analyze_from_folder(request: FolderRequest):
    try:
        agent_a_output = call_agent_a(request.folder_path)
    except AgentAError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Lỗi không xác định khi gọi Agent A: {str(e)}")

    try:
        return start_agent_b(agent_a_output)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent B lỗi: {str(e)}")


@app.post("/analyze", response_model=AnalyzeResponse, tags=["Agent B"])
def analyze(input_data: AgentAOutput):
    """Nhận trực tiếp AgentAOutput (server-to-server). Không raise lỗi khi
    success=False nữa — Agent B tự sinh report degrade tương ứng."""
    try:
        return start_agent_b(input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/mock", response_model=AnalyzeResponse, tags=["Agent B"])
def analyze_mock():
    try:
        return start_agent_b(MOCK_INPUT)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/{thread_id}/resume", response_model=ResumeResponse, tags=["Agent B"])
def analyze_resume(thread_id: str, decision: ApprovalDecision):
    """
    Xác nhận (approve) hoặc từ chối (reject) nội dung LLM sinh ra.

    Body ví dụ:
    - Approve:  {"approve": true}
    - Approve kèm sửa tay: {"approve": true, "edited_llm_output": {...}}
    - Reject (LLM sinh lại):  {"approve": false, "feedback": "Ghi rõ hơn rủi ro pháp lý"}
    """
    try:
        return resume_agent_b(thread_id, decision.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi resume: {str(e)}")