from pydantic import BaseModel
from typing import Optional, Any

class AgentResult(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None

class BaseAgent:
    """
    Base class for all Agents.
    Every agent must implement the run method, returning an AgentResult.
    """
    def run(self, input_data: dict) -> AgentResult:
        raise NotImplementedError("Each agent must implement the 'run' method.")
