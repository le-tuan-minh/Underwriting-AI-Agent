from fastapi import FastAPI
from app.schemas import AgentAOutput, AgentBOutput
from app.agent_b import run_agent_b
from app.mock_data import MOCK_INPUT

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Agent B đang chạy"}

@app.post("/analyze", response_model=AgentBOutput)
def analyze(input_data: AgentAOutput):
    return run_agent_b(input_data)

@app.post("/analyze/mock", response_model=AgentBOutput)
def analyze_mock():
    return run_agent_b(MOCK_INPUT)