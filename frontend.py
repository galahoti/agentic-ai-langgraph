import uuid

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from research_agent.utils.simple_chatbot import chatbot, return_all_threads


# =========================== Utilities ===========================
def generate_thread_id():
    return uuid.uuid4()

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state["thread_id"] = thread_id
    add_thread(thread_id)
    st.session_state["message_history"] = []

def add_thread(thread_id):
    if thread_id not in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].append(thread_id)

def load_conversation(thread_id):
    state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
    # Check if messages key exists in state values, return empty list if not
    return state.values.get("messages", [])

# ======================= Session Initialization ===================
if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()

if "chat_threads" not in st.session_state:
    st.session_state["chat_threads"] = return_all_threads()

add_thread(st.session_state["thread_id"])

# ============================ Sidebar ============================
st.sidebar.title("LangGraph Chatbot")

if st.sidebar.button("New Chat"):
    reset_chat()

st.sidebar.header("My Conversations")
for thread_id in st.session_state["chat_threads"][::-1]:
    if st.sidebar.button(str(thread_id)):
        st.session_state["thread_id"] = thread_id
        messages = load_conversation(thread_id)

        temp_messages = []
        for msg in messages:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            temp_messages.append({"role": role, "content": msg.content})
        st.session_state["message_history"] = temp_messages

# ============================ Main UI ============================

# Render history
for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        st.text(message["content"])

user_input = st.chat_input("Type here")

if user_input:
    # Show user's message
    st.session_state["message_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.text(user_input)

    CONFIG = {
        "configurable": {"thread_id": st.session_state["thread_id"]},
        "metadata": {"thread_id": st.session_state["thread_id"]},
        "run_name": "chat_turn",
    }

    # Assistant streaming block
    with st.chat_message("assistant"):
        def stream_processor():
                    full_response = ""
                    status_box = None
                    stream = chatbot.stream(
                        {"messages": [HumanMessage(content=user_input)]},
                        config=CONFIG,
                        stream_mode="updates",
                    )
                    
                    try:
                        for event in stream:
                            for node_name, state_update in event.items():
                                # Display tool usage with st.status
                                if node_name == "tools":
                                    tool_message = state_update["messages"][-1]
                                    tool_name = tool_message.name
                                    if status_box is None:
                                        status_box = st.status(f"🔧 Using `{tool_name}`…", expanded=True)
                                    else:
                                        status_box.update(label=f"🔧 Using `{tool_name}`…")
                                
                                # Stream the final response from the chatbot node
                                elif node_name == "chatbot" and "messages" in state_update:
                                    last_message = state_update["messages"][-1]
                                    
                                    # THE MAGIC FILTER: Only stream final AI answers
                                    if isinstance(last_message, AIMessage) and not last_message.tool_calls:
                                        content = last_message.content
                                        
                                        # Process list-based content (e.g., from Claude)
                                        if isinstance(content, list):
                                            for block in content:
                                                if block.get("type") == "text":
                                                    text_chunk = block.get("text", "")
                                                    full_response += text_chunk
                                                    yield text_chunk
                                        # Process simple string content
                                        elif isinstance(content, str):
                                            full_response += content
                                            yield content
                    finally:
                        # After the stream, save the complete message and update status
                        if status_box:
                            status_box.update(label="✅ Tool finished", state="complete", expanded=False)
                        if full_response:
                            st.session_state["message_history"].append(
                                {"role": "assistant", "content": full_response}
                            )

        # Use st.write_stream with our robust, intelligent processor
        st.write_stream(stream_processor)