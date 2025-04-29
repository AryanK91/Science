from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn
import socket
from start import rag_chain, HumanMessage, AIMessage
from user_data import user_data
import os
from dotenv import load_dotenv

load_dotenv()
 

app = FastAPI(title="Science AI Tutor API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://sciencetutor-api-804953929335.us-central1.run.app",
        "http://sciencetutor-api-804953929335.us-central1.run.app",
        "https://aitutor-theta.vercel.app",  
        "*"  # Allow all origins
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    username: str
    chat_history: Optional[List[ChatMessage]] = []

class ChatResponse(BaseModel):
    answer: str
    chat_history: List[ChatMessage]
    progress: Optional[Dict] = None

class ProgressResponse(BaseModel):
    username: str
    total_questions: int
    correct_answers: int
    accuracy: float
    topics_covered: List[str]
    last_session: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Create or get user
        user_data.create_user(request.username)
        
        # Convert chat history to the format expected by rag_chain
        formatted_history = []
        for msg in request.chat_history:
            if msg.role == "user":
                formatted_history.append(HumanMessage(content=msg.content))
            elif msg.role == "ai":
                formatted_history.append(AIMessage(content=msg.content))

        # Get response from rag_chain
        result = rag_chain.invoke({
            "input": request.message,
            "chat_history": formatted_history
        })

        # Update chat history
        new_history = request.chat_history + [
            ChatMessage(role="user", content=request.message),
            ChatMessage(role="ai", content=result["answer"])
        ]

        # Update user progress
        user_data.update_chat_history(request.username, request.message, True)
        user_data.update_chat_history(request.username, result["answer"], False)
        user_data.update_progress(request.username, "General Science", True)  # You might want to add topic detection

        # Get updated progress
        progress = user_data.get_progress(request.username)

        return ChatResponse(
            answer=result["answer"],
            chat_history=new_history,
            progress=progress
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/progress/{username}", response_model=ProgressResponse)
async def get_progress(username: str):
    progress = user_data.get_progress(username)
    if not progress:
        raise HTTPException(status_code=404, detail="User not found")
    return progress

@app.get("/")
async def root():
    return {"message": "Welcome to Science AI Tutor API"}

if __name__ == "__main__":
    try:
        port = int(os.getenv("port", 5173))
        google_api_key = os.getenv("GOOGLE_API_KEY")
        print(f"Starting server on port {port}")
        print(f"Access the API at http://localhost:{port}")
        print(f"Access the documentation at http://localhost:{port}/docs")
        uvicorn.run(app, host="0.0.0.0", port=port)
    except RuntimeError as e:
        print(f"Error: {e}")
        exit(1) 