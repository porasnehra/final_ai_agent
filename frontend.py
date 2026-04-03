import streamlit as st
import os
from ai_logic import chatbot  # Import directly!
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="AI Agent Assistant", page_icon="🤖")
st.title("🤖 AI Agent Assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What can I do for you?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # We call the chatbot directly here, no requests.post() needed!
        inputs = {"messages": [HumanMessage(content=prompt)]}
        config = {"configurable": {"thread_id": "render_user"}}
        
        result = chatbot.invoke(inputs, config)
        response = result["messages"][-1].content
        
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
