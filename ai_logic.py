import os
import json
from typing import Annotated, TypedDict, Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from notion_client import Client
from todoist_api_python.api import TodoistAPI

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def build_user_agent(credentials_dict: Dict[str, Any], checkpointer=None):
    """
    Creates an instance of the agent with compiled tools built specifically
    for the user's provided credentials.
    """
    
    @tool
    def create_calendar_event(summary: str, start_time: str, end_time: str):
        """
        Creates an event on Google Calendar. 
        Format: 'YYYY-MM-DDTHH:MM:SSZ' (e.g. '2026-03-31T15:00:00Z')
        """
        try:
            token_json = credentials_dict.get("google_token_json")
            if not token_json:
                return "Google Token JSON not provided. Cannot access calendar."
            
            creds = Credentials.from_authorized_user_info(json.loads(token_json))
            service = build('calendar', 'v3', credentials=creds)
            
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
            token = credentials_dict.get("notion_token")
            db_id = credentials_dict.get("notion_database_id")
            
            if not token or not db_id:
                return "Error: Notion credentials (token/db_id) missing."

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
            token = credentials_dict.get("todoist_api_token")
            if not token:
                return "Error: Todoist API token missing."
            
            api = TodoistAPI(token)
            task = api.add_task(content=content, due_string=due_date)
            return f"Todoist task '{task.content}' added (ID: {task.id})."
        except Exception as e:
            return f"Todoist Error: {str(e)}"

    tools = [create_calendar_event, create_notion_note, add_todoist_task]
    
    gemini_key = credentials_dict.get("google_api_key") or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
         raise Exception("Google Gemini API Key is required. Please set it in Settings -> Configure API Integrations, or define it as an Environment Variable.")
         
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        api_key=gemini_key,
        temperature=0
    )
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = SystemMessage(content=(
        "You are a highly capable AI Agent Assistant. "
        "When a user asks you to create a note or save information to Notion, "
        "immediately use the 'create_notion_note' tool. "
        "DO NOT ask the user for a Page ID, Database ID, or Workspace ID. "
        "Just generate a suitable title and summary based on the user's request."
    ))

    def assistant_node(state: AgentState):
        messages = [system_prompt] + state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState):
        last_message = state["messages"][-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        return END

    builder = StateGraph(AgentState)
    builder.add_node("assistant", assistant_node)
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "assistant")
    builder.add_conditional_edges("assistant", should_continue)
    builder.add_edge("tools", "assistant")

    if checkpointer is not None:
         return builder.compile(checkpointer=checkpointer)
    else:
         return builder.compile()
