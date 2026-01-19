import streamlit as st
from langraph_rag_backend import (
    get_chatbot, 
    retrieve_all_threads, 
    model, 
    submit_async_task,
    process_document,      
    remove_document,       
    get_rag_status    
)
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import uuid
import queue
import os
import tempfile


# ******************************************************  Page Config  ******************************************************

st.set_page_config(
    page_title="AI Chatbot with MCP",
    page_icon="🤖",
    layout="wide"
)


# ******************************************************  Utility Functions  ******************************************************

@st.dialog("Rename Chat")
def rename_dialog(thread_id):
    current_name = st.session_state['thread_titles'].get(thread_id, "New Chat")
    new_name = st.text_input("Enter new name:", value=current_name)
    
    if st.button("Save"):
        st.session_state['thread_titles'][thread_id] = new_name
        st.rerun()


def generate_thread_id():
    return str(uuid.uuid4())


def reset_chat():
    st.session_state['thread_id'] = generate_thread_id()
    st.session_state['message_history'] = []


def add_thread(thread_id):
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)


def load_conversation(thread_id):
    """Load conversation history from a specific thread"""
    try:
        chatbot_instance = st.session_state.get('chatbot')
        if chatbot_instance:
            state = chatbot_instance.get_state(
                config={'configurable': {'thread_id': thread_id}}
            )
            return state.values.get('messages', [])
    except Exception as e:
        st.error(f"Error loading conversation: {e}")
    return []


def model_title_generation(user_input, ai_message):
    """Generate a title for the conversation"""
    try:
        from langgraph_mcp_backend import model as backend_model
        
        if backend_model is None:
            return "New Chat"
        
        prompt = f"Generate ONLY a short title (max 5 words, no quotes or extra text) based on this conversation:\nUser: {user_input}\nAssistant: {ai_message}"
        title_response = backend_model.invoke(prompt)
        title = title_response.content.strip().replace('"', '').replace("'", '').strip()
        return title[:50]
    except Exception as e:
        print(f"Error generating title: {e}")
        return "New Chat"


# ******************************************************  Initialization  ******************************************************

if 'chatbot' not in st.session_state:
    with st.spinner('🤖 Initializing AI assistant... This may take a moment.'):
        try:
            st.session_state['chatbot'] = get_chatbot()
            st.session_state['initialized'] = True
        except Exception as e:
            st.error(f'❌ Failed to initialize chatbot: {e}')
            st.stop()

# ******************************************************  Session Setup  ******************************************************

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_threads' not in st.session_state:
    try:
        st.session_state['chat_threads'] = retrieve_all_threads() or []
    except Exception as e:
        print(f"Error retrieving threads: {e}")
        st.session_state['chat_threads'] = []

if 'thread_titles' not in st.session_state:
    st.session_state['thread_titles'] = {}


# ******************************************************  Sidebar UI  ******************************************************

with st.sidebar:
    st.title("💬 Chat")

    st.subheader("📚 Document")
    
    # Get current RAG status
    rag_status = get_rag_status()

    if rag_status['has_document']:
        # Document is loaded - show info and remove button
        doc_info = rag_status['document_info']
        st.success(f"✅ {doc_info['filename']}")
        st.caption(f"📄 {doc_info['pages']} pages • {doc_info['chunks']} chunks")
        
        if st.button("🗑️ Remove Document", use_container_width=True):
            with st.spinner("Removing document..."):
                remove_document()
                # No need to rebuild graph!
            st.success("Document removed!")
            st.rerun()
    
    else:
        # No document - show upload interface
        st.info("📤 Upload a PDF to enable document Q&A")
        
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=['pdf'],
            key='pdf_uploader',
            label_visibility="collapsed"
        )
        
        if uploaded_file is not None:
            if st.button("📥 Process Document", use_container_width=True):
                with st.spinner(f"Processing {uploaded_file.name}..."):
                    try:
                        # Save uploaded file temporarily
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            tmp_path = tmp_file.name
                        
                        # Process the document
                        result = process_document(tmp_path)
                        
                        if result['success']:
                            # No need to rebuild graph!
                            st.success(f"✅ Processed {result['info']['filename']}!")
                            st.rerun()
                        else:
                            st.error(f"❌ Error: {result['error']}")
                        
                        # Clean up temp file
                        os.unlink(tmp_path)
                    
                    except Exception as e:
                        st.error(f"❌ Failed to process: {e}")
    
    if st.button("➕ New Chat", use_container_width=True):
        reset_chat()
        st.rerun()
    
    st.divider()
    st.subheader("Your Chats")
    
    if st.session_state['chat_threads']:
        for thread_id in st.session_state['chat_threads'][::-1]:
            display_name = st.session_state['thread_titles'].get(thread_id, "New Chat")
            
            col1, col2 = st.columns([5, 1])
            
            with col1:
                if st.button(display_name, key=str(thread_id), use_container_width=True):
                    st.session_state['thread_id'] = thread_id
                    messages = load_conversation(thread_id)
                    
                    temp_message = []
                    for message in messages:
                        if isinstance(message, HumanMessage):
                            role = 'user'
                        elif isinstance(message, AIMessage):
                            role = 'ai'
                        else:
                            continue
                        
                        if message.content:
                            temp_message.append({'role': role, 'content': message.content})
                    
                    st.session_state['message_history'] = temp_message
                    st.rerun()
            
            with col2:
                if st.button("✏️", key=f"edit_{thread_id}"):
                    rename_dialog(thread_id)
    else:
        st.info("No chat history yet. Start a new conversation!")


# ******************************************************  Main UI  ******************************************************

st.title("🤖 AI Chatbot with MCP Tools")
st.caption("Powered by LangGraph and MCP")

# Display message history
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

# Chat input
user_input = st.chat_input('💬 Type your message here...')

if user_input:
    if st.session_state['thread_id'] not in st.session_state['chat_threads']:
        add_thread(st.session_state['thread_id'])

    st.session_state['message_history'].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    CONFIG = {
        'configurable': {'thread_id': st.session_state['thread_id']},
        "metadata": {'thread_id': st.session_state["thread_id"]},
        "run_name": st.session_state['thread_titles'].get(st.session_state["thread_id"], "New Chat")
    }

    with st.chat_message("ai"):
        status_holder = {"box": None}
        
        def ai_only_message():
            """Stream AI responses using queue-based communication"""
            chatbot_instance = st.session_state['chatbot']
            event_queue = queue.Queue()
            
            async def run_stream():
                """Async function that runs in background thread"""
                try:
                    async for message_chunk, metadata in chatbot_instance.astream(
                        {'messages': [HumanMessage(content=user_input)]},
                        config=CONFIG,
                        stream_mode='messages'
                    ):
                        event_queue.put((message_chunk, metadata))
                except Exception as exc:
                    event_queue.put(("error", exc))
                    import traceback
                    traceback.print_exc()
                finally:
                    event_queue.put(None)
            
            # Submit the async task to background thread
            submit_async_task(run_stream())
            
            # Process events from the queue
            while True:
                item = event_queue.get()
                if item is None:
                    break
                
                message_chunk, metadata = item
                
                if message_chunk == "error":
                    error_msg = str(metadata)
                    print(f"Stream error: {error_msg}")
                    
                    # Show user-friendly error message
                    if "400" in error_msg or "invalid_request_error" in error_msg:
                        yield "⚠️ I encountered a technical issue with the tool response. Let me try again..."
                    else:
                        yield f"⚠️ An error occurred: {error_msg[:200]}"
                    break
                
                # Handle tool messages
                if isinstance(message_chunk, ToolMessage):
                    tool_name = getattr(message_chunk, "name", "tool")
                    if status_holder["box"] is None:
                        status_holder["box"] = st.status(f"🔧 Using `{tool_name}` …", expanded=True)
                    else:
                        status_holder["box"].update(
                            label=f"🔧 Using `{tool_name}` …", 
                            state="running", 
                            expanded=True
                        )
                
                # Stream AI message content
                if isinstance(message_chunk, AIMessage) and message_chunk.content:
                    yield message_chunk.content
        
        ai_message = st.write_stream(ai_only_message())
        
        if status_holder["box"] is not None:
            status_holder["box"].update(label="✅ Tool finished", state="complete", expanded=False)
    
    st.session_state['message_history'].append({"role": "ai", "content": ai_message})
    
    if len(st.session_state['message_history']) == 2:
        title = model_title_generation(user_input, ai_message)
        st.session_state['thread_titles'][st.session_state['thread_id']] = title