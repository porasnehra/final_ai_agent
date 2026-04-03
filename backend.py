from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from ai_logic import chatbot  # Ensure ai_logic.py has 'chatbot = builder.compile(...)'
from langchain_core.messages import HumanMessage
import uvicorn

app = FastAPI()

class ChatRequest(BaseModel):
    message: str
    thread_id: str

async def stream_generator(message: str, thread_id: str):
    """
    This is the proper way to handle the stream. 
    It extracts the text content and yields it chunk by chunk.
    """
    config = {"configurable": {"thread_id": thread_id}}
    input_data = {"messages": [HumanMessage(content=message)]}

    # We use .astream (async stream) for FastAPI compatibility
    async for msg, metadata in chatbot.astream(input_data, config, stream_mode="messages"):
        # LangGraph 'messages' mode yields chunks. 
        # We need to extract the text content and ignore empty chunks or metadata lists.
        if hasattr(msg, "content") and msg.content:
            # Sometimes msg.content can be a list (multi-modal), so we convert to string
            if isinstance(msg.content, str):
                yield msg.content
            elif isinstance(msg.content, list):
                for part in msg.content:
                    if isinstance(part, dict) and "text" in part:
                        yield part["text"]
                    elif isinstance(part, str):
                        yield part

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    # We call our generator and return it as a StreamingResponse
    return StreamingResponse(
        stream_generator(req.message, req.thread_id), 
        media_type="text/plain"
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)