from fastapi import FastAPI, HTTPException
from app_groq.schemas import AgentAOutput, AgentBOutput
from app_groq.agent_b import run_agent_b
from app_groq.mock_data import MOCK_INPUT

app = FastAPI(
    title="Agent B – Report Thẩm Định Hồ Sơ",
    description=(
        "Nhận output từ Agent A (phân loại & đối chiếu checklist), "
        "sinh report cảnh báo chất lượng, chứng từ thiếu, và đề xuất hành động."
    ),
    version="2.0.0",
)


@app.get("/", tags=["Health"])
def root():
    return {"message": "Agent B đang chạy", "version": "2.0.0"}


@app.post("/analyze", response_model=AgentBOutput, tags=["Agent B"])
def analyze(input_data: AgentAOutput):
    """
    Nhận output thực từ Agent A và trả về report thẩm định.

    Body phải theo đúng schema AgentAOutput:
    - analysis: str
    - matched_documents: list[MatchedDocument]
    - missing_documents: list[str]
    - is_eligible_for_review: bool
    """
    try:
        return run_agent_b(input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/mock", response_model=AgentBOutput, tags=["Agent B"])
def analyze_mock():
    """
    Chạy Agent B với mock data (dùng khi Agent A chưa deploy).
    Không cần body, tự động dùng MOCK_INPUT.
    """
    try:
        return run_agent_b(MOCK_INPUT)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))