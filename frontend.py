import streamlit as st
import requests

import os

API_URL = os.getenv("API_URL", "https://final-ai-agent-1.onrender.com/")

st.set_page_config(page_title="Multi-User Agent", page_icon="🤖")
st.title("🤖 Personal AI Assistant")

if "access_token" not in st.session_state:
    st.session_state["access_token"] = None
if "messages" not in st.session_state:
    st.session_state["messages"] = []

def login():
    with st.sidebar.form("Login Form"):
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            resp = requests.post(f"{API_URL}/login", data={"username": username, "password": password})
            if resp.status_code == 200:
                st.session_state["access_token"] = resp.json().get("access_token")
                st.session_state["messages"] = [] # reset chat on login
                st.success("Successfully logged in!")
                st.rerun()
            else:
                st.error("Invalid credentials.")

def register():
    with st.sidebar.form("Register Form"):
        st.subheader("Register")
        username = st.text_input("New Username")
        password = st.text_input("New Password", type="password")
        if st.form_submit_button("Register"):
            resp = requests.post(f"{API_URL}/register", json={"username": username, "password": password})
            if resp.status_code == 200:
                st.success("Registered successfully! You can now log in.")
            else:
                st.error(resp.json().get("detail", "Error registering"))

if not st.session_state["access_token"]:
    st.sidebar.title("Authentication")
    tab1, tab2 = st.sidebar.tabs(["Login", "Register"])
    with tab1:
        login()
    with tab2:
        register()
    st.info("Please log in from the sidebar to interact with the assistant.")

else:
    st.sidebar.title("Settings & Session")
    if st.sidebar.button("Logout"):
        st.session_state["access_token"] = None
        st.session_state["messages"] = []
        st.rerun()
        
    headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}

    # Fetch creds
    @st.cache_data(ttl=1)  # cache briefly so we don't spam api
    def fetch_creds():
        return requests.get(f"{API_URL}/credentials", headers=headers).json()

    with st.expander("⚙️ Configure API Integrations"):
        creds = fetch_creds()
        with st.form("creds_form"):
            google_api_key = st.text_input("Google Gemini API Key", value=creds.get("google_api_key") or "")
            google_token_json = st.text_area("Google Calendar Token (JSON)", value=creds.get("google_token_json") or "", help="Generated OAuth token.json for calendar")
            notion_token = st.text_input("Notion Token", value=creds.get("notion_token") or "")
            notion_database_id = st.text_input("Notion Database ID", value=creds.get("notion_database_id") or "")
            todoist_api_token = st.text_input("Todoist API Token", value=creds.get("todoist_api_token") or "")
            
            if st.form_submit_button("Save Credentials"):
                payload = {
                    "google_api_key": google_api_key,
                    "google_token_json": google_token_json,
                    "notion_token": notion_token,
                    "notion_database_id": notion_database_id,
                    "todoist_api_token": todoist_api_token
                }
                res = requests.post(f"{API_URL}/credentials", json=payload, headers=headers)
                if res.status_code == 200:
                    st.success("Credentials saved!")
                    fetch_creds.clear() # clear cache
                else:
                    st.error("Error saving properties")
                    
    # Chat UI
    st.divider()
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    if prompt := st.chat_input("Ask your assistant..."):
        st.session_state["messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        with st.spinner("Thinking..."):
            res = requests.post(f"{API_URL}/chat", json={"messages": st.session_state["messages"]}, headers=headers)
            if res.status_code == 200:
                reply = res.json().get("reply", "")
                st.session_state["messages"].append({"role": "assistant", "content": reply})
                with st.chat_message("assistant"):
                    st.markdown(reply)
            else:
                error_detail = res.json().get("detail", res.text)
                st.error(f"Error from server: {error_detail}")
                st.session_state["messages"].pop() # remove last user msg if failed
