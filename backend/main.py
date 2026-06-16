from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.settings import Settings
settings = Settings()
from pydantic import BaseModel
from src.agent_graph import graph

app = FastAPI(title="Secure Agentic RAG Endpoint Cluster", version="1.0")

class ChatRequest(BaseModel):
    message: str
    user_id: str
    role: str

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if hasattr(settings, 'CORS_ORIGINS') else ["*"],
    allow_methods=settings.CORS_METHODS if hasattr(settings, 'CORS_METHODS') else ["*"],
    allow_headers=settings.CORS_HEADERS if hasattr(settings, 'CORS_HEADERS') else ["*"],
    )
@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": settings.app_name,
        "version": settings.app_version
    }

@app.post("/api/chat")
async def process_chat_message(payload: ChatRequest):
    try:
        initial_state = {
            "query": payload.message,
            "current_user": payload.user_id,
            "user_role": payload.role,
            "retrieved_docs": [],
            "generated_response": "",
            "retry_count": 0,
            "is_valid": False,
            "evaluation_feedback": ""
        }
        
        result = graph.invoke(initial_state)
        return {"response": result["generated_response"]}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
