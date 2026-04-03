import os
from typing import Annotated, TypedDict
from dotenv import load_dotenv

# LangChain & LangGraph Imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

# Google Calendar API Imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Notion & Todoist Imports
from notion_client import Client
from todoist_api_python.api import TodoistAPI

# --- 1. SETUP & AUTH ---
load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/calendar']
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def get_calendar_service():
    """Handles Google OAuth2 authentication via Environment Variables."""
    creds = None
    
    # 1. Try to load the REFRESH TOKEN (token.json equivalent)
    token_json = os.getenv("GOOGLE_TOKEN_JSON")
    if token_json:
        creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    
    # 2. If no valid creds, try to use the CLIENT SECRETS (credentials.json equivalent)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # On Render, we can't run a local server for login.
            # We must load the credentials from an env var.
            creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
            if not creds_json:
                raise Exception("Google Credentials not found in environment variables!")
            
            # Use the dictionary directly instead of a filename
            creds_info = json.loads(creds_json)
            flow = InstalledAppFlow.from_client_config(creds_info, SCOPES)
            
            # NOTE: run_local_server() only works on your PC. 
            # For Render, you must have a valid GOOGLE_TOKEN_JSON already set.
            creds = flow.run_local_server(port=0)

    return build('calendar', 'v3', credentials=creds)
# --- 2. THE TOOLS ---

@tool
def create_calendar_event(summary: str, start_time: str, end_time: str):
    """
    Creates an event on Google Calendar. 
    Format: 'YYYY-MM-DDTHH:MM:SSZ' (e.g. '2026-03-31T15:00:00Z')
    """
    try:
        service = get_calendar_service()
        event = {
            'summary': summary,
            'start': {'dateTime': start_time, 'timeZone': 'UTC'},
            'end': {'dateTime': end_time, 'timeZone': 'UTC'},
        }
        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Calendar event created: {event.get('htmlLink')}"
    except Exception as e:
        return f"Calendar Error: {str(e)}"

@tool
def create_notion_note(title: str, content: str):
    """
    Creates a new note in Notion. 
    ONLY provide the 'title' and 'content'. 
    The Database ID is handled automatically by the system.
    """
    try:
        token = os.getenv("NOTION_TOKEN")
        db_id = os.getenv("NOTION_DATABASE_ID")
        
        if not token or not db_id:
            return "Error: Notion credentials missing from .env."

        notion = Client(auth=token)
        notion.pages.create(
            parent={"database_id": db_id},
            properties={"Name": {"title": [{"text": {"content": title}}]}},
            children=[{
                "object": "block", 
                "type": "paragraph", 
                "paragraph": {"rich_text": [{"text": {"content": content}}]}
            }]
        )
        return f"Successfully created Notion note: '{title}'"
    except Exception as e:
        return f"Notion API Error: {str(e)}"

@tool
def add_todoist_task(content: str, due_date: str = "today"):
    """Adds a task to your Todoist inbox."""
    try:
        api = TodoistAPI(os.getenv("TODOIST_API_TOKEN"))
        task = api.add_task(content=content, due_string=due_date)
        return f"Todoist task '{task.content}' added (ID: {task.id})."
    except Exception as e:
        return f"Todoist Error: {str(e)}"

# --- 3. AGENT GRAPH SETUP ---

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# Model setup
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0
)

tools = [create_calendar_event, create_notion_note, add_todoist_task]
llm_with_tools = llm.bind_tools(tools)

# FIXED: System Instruction to prevent the "I need a Database ID" error
system_prompt = SystemMessage(content=(
    "You are a highly capable AI Agent Assistant. "
    "When a user asks you to create a note or save information to Notion, "
    "immediately use the 'create_notion_note' tool. "
    "DO NOT ask the user for a Page ID, Database ID, or Workspace ID. "
    "Those IDs are already managed by the backend tools. "
    "Just generate a suitable title and summary based on the user's request."
))

# def assistant_node(state: AgentState):
#     """The assistant node now includes the system prompt to guide the AI."""
#     # We combine the system prompt with the conversation history
#     full_messages = [system_prompt] + state["messages"]
#     return {"messages": [llm_with_tools.invoke(full_messages)]}

def assistant_node(state: AgentState):
    """The assistant node ensures the system prompt is always at the top."""
    # This prevents the AI from 'forgeting' its instructions during long chats
    messages = [system_prompt] + state["messages"]
    
    # We invoke the LLM with the injected system instruction
    response = llm_with_tools.invoke(messages)
    
    return {"messages": [response]}

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

# Build the Graph
builder = StateGraph(AgentState)
builder.add_node("assistant", assistant_node)
builder.add_node("tools", ToolNode(tools))

builder.add_edge(START, "assistant")
builder.add_conditional_edges("assistant", should_continue)
builder.add_edge("tools", "assistant")

chatbot = builder.compile(checkpointer=MemorySaver())
