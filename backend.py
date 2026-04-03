import hashlib
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any

from database import SessionLocal, User, UserCredentials, engine
from ai_logic import build_user_agent
from langchain_core.messages import HumanMessage, AIMessage

app = FastAPI(title="Multi-User AI Agent API")

# Setup CORS if Streamlit runs on different port later
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Basic hashing
def get_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return get_password_hash(plain_password) == hashed_password

# Dependencies
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # very basic token: "user_uuid_or_id"
    # For this basic implementation, we just encode the ID in the token string itself
    # e.g. token is "fake-token-1"
    if not token.startswith("fake-token-"):
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        user_id = int(token.replace("fake-token-", ""))
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token format")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
         raise HTTPException(status_code=401, detail="User not found")
    return user


# ---------------- API MODELS ----------------

class UserCreate(BaseModel):
    username: str
    password: str

class CredentialsUpdate(BaseModel):
    google_api_key: Optional[str] = None
    google_token_json: Optional[str] = None
    notion_token: Optional[str] = None
    notion_database_id: Optional[str] = None
    todoist_api_token: Optional[str] = None

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]] # [{'role': 'user', 'content': 'hi'}]

# ---------------- ENDPOINTS ----------------

@app.post("/register")
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed = get_password_hash(user_data.password)
    new_user = User(username=user_data.username, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Initialize empty credentials
    creds = UserCredentials(user_id=new_user.id)
    db.add(creds)
    db.commit()
    
    return {"message": "User registered successfully"}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    return {"access_token": f"fake-token-{user.id}", "token_type": "bearer"}

@app.get("/credentials")
def get_credentials(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    creds = db.query(UserCredentials).filter(UserCredentials.user_id == current_user.id).first()
    if not creds:
        return {}
    return {
        "google_api_key": creds.google_api_key,
        "google_token_json": creds.google_token_json,
        "notion_token": creds.notion_token,
        "notion_database_id": creds.notion_database_id,
        "todoist_api_token": creds.todoist_api_token
    }

@app.post("/credentials")
def update_credentials(creds_data: CredentialsUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    creds = db.query(UserCredentials).filter(UserCredentials.user_id == current_user.id).first()
    if not creds:
        creds = UserCredentials(user_id=current_user.id)
        db.add(creds)
    
    # Update fields
    if creds_data.google_api_key is not None:
        creds.google_api_key = creds_data.google_api_key
    if creds_data.google_token_json is not None:
        creds.google_token_json = creds_data.google_token_json
    if creds_data.notion_token is not None:
        creds.notion_token = creds_data.notion_token
    if creds_data.notion_database_id is not None:
        creds.notion_database_id = creds_data.notion_database_id
    if creds_data.todoist_api_token is not None:
        creds.todoist_api_token = creds_data.todoist_api_token
        
    db.commit()
    return {"message": "Credentials updated successfully"}

@app.post("/chat")
def chat(request: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    creds = db.query(UserCredentials).filter(UserCredentials.user_id == current_user.id).first()
    if not creds:
        raise HTTPException(status_code=400, detail="User credentials not initialized")
    
    creds_dict = {
        "google_api_key": creds.google_api_key,
        "google_token_json": creds.google_token_json,
        "notion_token": creds.notion_token,
        "notion_database_id": creds.notion_database_id,
        "todoist_api_token": creds.todoist_api_token
    }
    
    import os
    # ensure gemini key exists
    has_env_key = bool(os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"))
    if not creds_dict["google_api_key"] and not has_env_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is missing. Please save it in settings or provide it as an environment variable.")
        
    try:
        agent = build_user_agent(creds_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    # convert messages dicts to Langchain Messages
    langchain_msgs = []
    for m in request.messages:
        if m["role"] == "user":
            langchain_msgs.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
             langchain_msgs.append(AIMessage(content=m["content"]))
             
    try:
         result = agent.invoke({"messages": langchain_msgs})
         # The last message is the reply from the agent.
         final_reply = result["messages"][-1].content
         return {"reply": final_reply}
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Graph Execution Error: {str(e)}")
