from typing import TypedDict, List, Dict, Any

class AgentState(TypedDict):
    query: str
    current_user: str
    user_role: str
    retrieved_docs: List[Dict[str, Any]]
    generated_response: str
    retry_count: int
    is_valid: bool
    evaluation_feedback: str
