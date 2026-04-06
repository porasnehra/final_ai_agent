# 🤖 Multi-User AI Agent System (FastAPI + LangGraph + Streamlit)

This project is a sophisticated **Multi-Agent Orchestrator** built to handle personal productivity tasks across multiple platforms. Unlike simple chatbots, this system uses **LangGraph** to maintain state, **FastAPI** for a scalable streaming backend, and **SQLite** for persistent local logging.

---

## 🌟 Key Features
* **Multi-User Authentication**: Secure registration and login with hashed passwords.
* **Dynamic Tool Routing**: Uses LLM logic to decide between Google Calendar, Notion, or Todoist.
* **Stateful Memory**: Remembers user context across chat sessions using LangGraph `MemorySaver`.
* **Streaming UI**: Real-time token delivery in Streamlit via FastAPI `StreamingResponse`.
* **Local Persistence**: Automated logging of agent actions into a local SQLite database.

---

## 🛠️ Detailed Project Architecture

The system is decoupled into three primary layers:
1.  **The Brain (`ai_logic.py`)**: Defines the LangGraph state machine, binds tools, and manages the "Supervisor" LLM logic.
2.  **The Engine (`backend.py`)**: A FastAPI server that handles user sessions, database interactions (SQLAlchemy), and streams AI chunks.
3.  **The Face (`frontend.py`)**: A Streamlit dashboard where users manage credentials and chat with their agent.

---

## 🔑 Setup Guide: API Keys & Credentials

To run this project, you need to gather four primary credentials. Follow these steps exactly:

### 1. Google Calendar API (`credentials.json`)
This is the most complex part of the setup as it requires OAuth2.
1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  **Create a New Project** named "AI Agent".
3.  Navigate to **APIs & Services > Library** and search for **"Google Calendar API"**. Click **Enable**.
4.  Go to **OAuth Consent Screen**:
    * Choose **External**.
    * Fill in the app name and your email.
    * **Crucial:** Add your email as a **Test User** (under the "Test Users" section).
5.  Go to **Credentials > Create Credentials > OAuth Client ID**:
    * Application Type: **Desktop App**.
    * Name it and click **Create**.
6.  Click the **Download JSON** icon for the client you just created.
7.  **Rename** this file to `credentials.json` and place it in the `mf_ai_agent/` folder.

### 2. Google Gemini API Key
1.  Visit [Google AI Studio](https://aistudio.google.com/).
2.  Click on **"Get API Key"**.
3.  Copy the key and add it to your `.env` file as `GOOGLE_API_KEY`.

### 3. Todoist API Token
1.  Login to your [Todoist Web App](https://todoist.com/).
2.  Go to **Settings > Integrations > Developer**.
3.  Copy your **API Token** and add it to `.env` as `TODOIST_API_TOKEN`.

### 4. Notion Integration
1.  Go to [Notion My Integrations](https://www.notion.so/my-integrations).
2.  Click **+ New Integration**, name it, and submit.
3.  Copy the **Internal Integration Token** (`NOTION_TOKEN`).
4.  **Database Setup:** Open the Notion database you want to use. Click the **"..."** (top right) > **Connect to** > Search for your Integration name.
5.  Copy the **Database ID** from the URL (the string between `notion.so/` and `?v=`).

---

## 🚀 Step-by-Step Installation

### 1. Environment Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure `.env`
Create a `.env` file in the root directory:
```text
GOOGLE_API_KEY=your_gemini_key
NOTION_TOKEN=your_notion_token
NOTION_DATABASE_ID=your_notion_db_id
TODOIST_API_TOKEN=your_todoist_token
```

### 3. Run the System
You must run both the backend and frontend simultaneously.

**Terminal 1 (Backend):**
```bash
fastapi run backend.py
```

**Terminal 2 (Frontend):**
```bash
streamlit run frontend.py
```

---

## 📂 File Structure
```text
├── mf_ai_agent/
│   ├── ai_logic.py          # LangGraph & LLM Logic
│   ├── backend.py           # FastAPI & OAuth Endpoints
│   ├── database.py          # SQLAlchemy Models (SQLite)
│   ├── frontend.py          # Streamlit UI
│   ├── credentials.json     # Google OAuth File (User Generated)
│   └── .env                 # API Keys (User Generated)
├── requirements.txt         # Project Dependencies
└── README.md                # Project Documentation
```

---

## ⚠️ Troubleshooting
* **OAuth Window Not Opening:** Ensure you are running the backend locally. Google OAuth requires a local callback.
* **Model Not Found (404):** Ensure `ai_logic.py` uses `model="gemini-1.5-flash-latest"`.
* **Database Locked:** Close any SQLite viewer tools before running the backend.
