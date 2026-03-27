import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .main import DocumentQA

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Bharatiyam AI Assistant API")

qa_system = None
try:
    qa_system = DocumentQA()
    logger.info("DocumentQA system initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize DocumentQA: {str(e)}")
    raise

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str
    language: str = "auto"
    session_id: Optional[str] = None
    history_limit: Optional[int] = None
    return_history: bool = True
    user_id: Optional[str] = None


class QueryResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]] = []
    session_id: str
    history: Optional[List[Dict[str, Any]]] = None


@app.get("/")
async def read_root():
    return {"message": "Bharatiyam AI Assistant API is running"}


@app.post("/query", response_model=QueryResponse)
async def query(payload: QueryRequest):
    if not qa_system:
        raise HTTPException(status_code=500, detail="QA system not initialized")

    try:
        result = qa_system.query(
            payload.query,
            language=payload.language,
            session_id=payload.session_id,
            history_limit=payload.history_limit,
            user_id=payload.user_id,
        )

        response_text = result.get("answer", "No response generated")
        sources_data = result.get("sources", [])
        session_id = result.get("session_id")
        history_data = result.get("history") if payload.return_history else None

        response_payload = {
            "response": response_text,
            "sources": sources_data,
            "session_id": session_id or "",
            "history": history_data,
        }
        return response_payload
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversations")
async def list_conversations(
    user_id: str = Query(..., description="User identifier"),
):
    if not qa_system:
        raise HTTPException(status_code=500, detail="QA system not initialized")

    try:
        collection = qa_system.conversations
        docs = collection.find(
            {"user_id": user_id},
            {"_id": 0, "session_id": 1, "updated_at": 1}
        ).sort("updated_at", -1)

        conversations = [
            {
                "_id": doc["session_id"],
                "title": f"Chat {doc['session_id'][:8]}",
                "createdAt": doc.get("updated_at", ""),
                "messages": []
            }
            for doc in docs
        ]
        return {"conversations": conversations}
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history")
async def get_history(
    session_id: str = Query(..., description="Conversation session identifier"),
    user_id: str = Query(..., description="User identifier"),
    limit: Optional[int] = Query(None, ge=1),
):
    if not qa_system:
        raise HTTPException(status_code=500, detail="QA system not initialized")

    history = qa_system.get_history(session_id, limit, user_id)
    return {"session_id": session_id, "history": history}


@app.delete("/history")
async def delete_history(
    session_id: str = Query(..., description="Conversation session identifier"),
    user_id: str = Query(..., description="User identifier")
):
    if not qa_system:
        raise HTTPException(status_code=500, detail="QA system not initialized")

    qa_system.clear_history(session_id, user_id)
    return {"session_id": session_id, "status": "cleared"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
