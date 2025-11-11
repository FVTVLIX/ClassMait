# app.py
# import streamlit as st
# from rag_system import RAGSystem
# import tempfile
# import os

# st.title("🧠 AI Learning Assistant")
# st.write("Upload a textbook, set your level, and start learning!")

# # Initialize session state for the RAG system and chat history
# if "rag" not in st.session_state:
#     st.session_state.rag = None
# if "messages" not in st.session_state:
#     st.session_state.messages = []

# # Sidebar for PDF upload and settings
# with st.sidebar:
#     uploaded_file = st.file_uploader("Upload a Textbook (PDF)", type="pdf")
#     user_level = st.selectbox("Select your level", ("Beginner", "Intermediate", "Expert"))
#     if uploaded_file is not None:
#         if st.button("Process Textbook"):
#             with st.spinner('Processing PDF...'):
#                 # Save uploaded file to a temporary file
#                 with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
#                     tmp_file.write(uploaded_file.getvalue())
#                     tmp_file_path = tmp_file.name
#                 # Initialize and ingest
#                 st.session_state.rag = RAGSystem()
#                 st.session_state.rag.ingest_pdf(tmp_file_path)
#                 os.unlink(tmp_file_path) # Delete temp file
#             st.success("Textbook processed and loaded!")

# # Main chat interface
# if st.session_state.rag is None:
#     st.info("👈 Please upload a PDF textbook to begin.")
# else:
#     # Display chat history
#     for message in st.session_state.messages:
#         with st.chat_message(message["role"]):
#             st.markdown(message["content"])

#     # React to user input
#     if prompt := st.chat_input("What is your question?"):
#         # Display user message in chat message container
#         st.chat_message("user").markdown(prompt)
#         # Add user message to chat history
#         st.session_state.messages.append({"role": "user", "content": prompt})

#         # Get assistant response
#         with st.spinner("Thinking..."):
#             response = st.session_state.rag.get_answer(prompt, user_level)
#         # Display assistant response in chat message container
#         with st.chat_message("assistant"):
#             st.markdown(response)
#         # Add assistant response to chat history
#         st.session_state.messages.append({"role": "assistant", "content": response})

# -------------------------------------------------
#  app.py
# -------------------------------------------------
import os
import time
import tempfile
import json
import uuid
from datetime import datetime
import streamlit as st
from pathlib import Path

# -------------------------------------------------
#  Page Configuration (must be first Streamlit command)
# -------------------------------------------------
st.set_page_config(
    page_title="ClassMateAI - Your Learning Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="auto",
)

# -------------------------------------------------
#  Your own RAG wrapper (make sure it works with the API key)
# -------------------------------------------------
from rag_system import RAGSystem   # <-- keep this file unchanged except for optional api_key param

# -------------------------------------------------
#  Session‑state defaults (run only once per session)
# -------------------------------------------------
if "step" not in st.session_state:
    st.session_state.step = 0               # 0=home, 1=api, 2=upload, 3=level, 4=process, 5=chat

if "api_key" not in st.session_state:
    st.session_state.api_key = ""

if "uploaded_path" not in st.session_state:
    st.session_state.uploaded_path = None   # absolute path string

if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None

if "level" not in st.session_state:
    st.session_state.level = "Beginner"

if "rag" not in st.session_state:
    st.session_state.rag = None

# NEW: Chat history management
if "chat_threads" not in st.session_state:
    st.session_state.chat_threads = []      # list of thread objects: {"id": str, "title": str, "timestamp": str, "messages": []}

if "current_thread_id" not in st.session_state:
    st.session_state.current_thread_id = None

# DEPRECATED: Keep for backward compatibility, but we'll use chat_threads now
if "messages" not in st.session_state:
    st.session_state.messages = []          # list of dicts: {"role": "user"/"assistant", "content": "..."} 

# -------------------------------------------------
#  Helper: write uploaded file to a *named* temp file
# -------------------------------------------------
def save_uploaded_file(uploaded_file) -> str:
    """
    Takes a Streamlit UploadedFile object, writes it to a NamedTemporaryFile,
    and returns the *absolute* path as a string.
    The file is NOT deleted here – we will delete it after ingestion.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getvalue())
        return tmp.name  # <-- returns something like /var/folders/.../tmpabcd1234.pdf

# -------------------------------------------------
#  Chat History Helper Functions
# -------------------------------------------------
def create_new_thread():
    """Creates a new chat thread and sets it as current."""
    thread_id = str(uuid.uuid4())
    new_thread = {
        "id": thread_id,
        "title": "New Conversation",
        "timestamp": datetime.now().isoformat(),
        "messages": []
    }
    st.session_state.chat_threads.insert(0, new_thread)  # Add to beginning
    st.session_state.current_thread_id = thread_id

    # Keep only last 10 threads
    if len(st.session_state.chat_threads) > 10:
        st.session_state.chat_threads = st.session_state.chat_threads[:10]

def get_current_thread():
    """Returns the current active thread, or creates one if none exists."""
    if not st.session_state.current_thread_id:
        create_new_thread()

    for thread in st.session_state.chat_threads:
        if thread["id"] == st.session_state.current_thread_id:
            return thread

    # If thread not found, create new one
    create_new_thread()
    return get_current_thread()

def switch_thread(thread_id):
    """Switches to a different chat thread."""
    st.session_state.current_thread_id = thread_id

def delete_thread(thread_id):
    """Deletes a chat thread."""
    st.session_state.chat_threads = [t for t in st.session_state.chat_threads if t["id"] != thread_id]

    # If we deleted the current thread, create a new one
    if st.session_state.current_thread_id == thread_id:
        if st.session_state.chat_threads:
            st.session_state.current_thread_id = st.session_state.chat_threads[0]["id"]
        else:
            create_new_thread()

def update_thread_title(thread, first_message):
    """Updates thread title based on first message (truncate to 40 chars)."""
    if thread["title"] == "New Conversation" and first_message:
        thread["title"] = first_message[:40] + "..." if len(first_message) > 40 else first_message

def format_timestamp(iso_timestamp):
    """Formats ISO timestamp to readable format."""
    dt = datetime.fromisoformat(iso_timestamp)
    now = datetime.now()

    # If today, show time
    if dt.date() == now.date():
        return dt.strftime("%I:%M %p")
    # If this year, show month and day
    elif dt.year == now.year:
        return dt.strftime("%b %d")
    # Otherwise show year
    else:
        return dt.strftime("%b %d, %Y")

# -------------------------------------------------
#  Navigation bar (appears at the top of every page except home)
# -------------------------------------------------
def nav_bar():
    col_left, col_center, col_right = st.columns([1, 6, 1])

    # ← Back button (disabled on the very first step)
    with col_left:
        if st.session_state.step > 0:
            if st.button("← Back", key="nav_back"):
                st.session_state.step -= 1
                st.rerun()
        else:
            st.write("")   # placeholder for layout symmetry

    # Step indicator (center)
    with col_center:
        st.markdown(
            f"<h4 style='text-align:center; margin:0;'>Step {st.session_state.step + 1} of 6</h4>",
            unsafe_allow_html=True,
        )

    # Right side empty (keeps layout balanced)
    with col_right:
        st.write("")
    st.markdown("---")

# -------------------------------------------------
#  PAGE 0 – HOME
# -------------------------------------------------
def page_home():
    """Welcome screen – the only page without a nav bar."""
    st.markdown(
        """
        <div style="text-align:center;">
            <h1 style="font-size:3rem;
                       background:linear-gradient(135deg,#6a11cb,#2575fc);
                       -webkit-background-clip:text;
                       -webkit-text-fill-color:transparent;">
                ClassMateAI
            </h1>
            <p style="font-size:1.3rem; color:#4a5568;">
                Your Personal AI Learning Assistant
            </p>
            <div style="height:250px; margin:1rem auto;
                        display:flex; align-items:center; justify-content:center;
                        background:#f0f4ff; border-radius:15px;">
                <p style="color:#6a11cb;">[Animation placeholder]</p>
            </div>
            <p style="font-size:1.1rem; max-width:800px; margin:0 auto;">
                Transform any textbook into an interactive learning experience
                with personalized explanations and quizzes.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Centered “Get Started” button
    if st.button("Get Started →", key="home_start", use_container_width=True):
        st.session_state.step = 1   # move to API‑key page
        st.rerun()

# -------------------------------------------------
#  PAGE 1 – API KEY
# -------------------------------------------------
def page_api_key():
    nav_bar()

    st.markdown(
        """
        ## 🔑 OpenAI API Key
        Enter your OpenAI API key so the assistant can call GPT‑4.
        You can create a key at
        <a href="https://platform.openai.com/account/api-keys" target="_blank">
        platform.openai.com/account/api-keys</a>.
        """,
        unsafe_allow_html=True,
    )

    api_key = st.text_input(
        "API Key",
        type="password",
        placeholder="sk-…",
        value=st.session_state.api_key,
        key="api_key_input",
    )

    # Save the key as soon as the user types it
    if api_key:
        st.session_state.api_key = api_key
        os.environ["OPENAI_API_KEY"] = api_key   # needed for OpenAIEmbeddings / ChatOpenAI

    # Forward button (disabled until a key is entered)
    col_left, col_center, col_right = st.columns([1, 6, 1])
    with col_center:
        if st.button(
            "Continue →",
            key="api_continue",
            disabled=not api_key,
            use_container_width=True,
        ):
            st.session_state.step = 2   # go to upload page
            st.rerun()

# -------------------------------------------------
#  PAGE 2 – UPLOAD PDF
# -------------------------------------------------
def page_upload():
    nav_bar()

    st.markdown("## 📚 Upload Your Textbook (PDF)")

    uploaded = st.file_uploader(
        "Drag‑and‑drop a PDF file here", type="pdf", label_visibility="collapsed"
    )

    if uploaded:
        # Save to a *named* temporary file
        tmp_path = save_uploaded_file(uploaded)
        st.session_state.uploaded_path = tmp_path
        
        # NEW: Store the PDF bytes for later re-creation
        st.session_state.pdf_bytes = uploaded.getvalue()  # ← Add this line
        
        st.success("File uploaded – you can now continue.")

    # Forward button
    col_left, col_center, col_right = st.columns([1, 6, 1])
    with col_center:
        if st.button(
            "Continue →",
            key="upload_continue",
            disabled=st.session_state.uploaded_path is None,
            use_container_width=True,
        ):
            st.session_state.step = 3
            st.rerun()

# -------------------------------------------------
#  PAGE 3 – SELECT LEARNING LEVEL
# -------------------------------------------------
def page_level():
    nav_bar()

    st.markdown("## 🎯 Choose Your Learning Level")

    level = st.radio(
        "Select level:",
        ("Beginner", "Intermediate", "Expert"),
        index=("Beginner", "Intermediate", "Expert").index(st.session_state.level),
        key="level_radio",
    )
    st.session_state.level = level

    col_left, col_center, col_right = st.columns([1, 6, 1])
    with col_center:
        if st.button("Process Textbook →", key="process_start", use_container_width=True):
            st.session_state.step = 4   # go to processing page
            st.rerun()

# -------------------------------------------------
#  PAGE 4 – PROCESSING (the step that used to error)
# -------------------------------------------------
def page_processing():
    nav_bar()
    
    # NEW: Re-create PDF file if it was deleted
    if (st.session_state.uploaded_path and 
        not Path(st.session_state.uploaded_path).is_file()):
        # File was deleted, re-create it from stored bytes
        with open(st.session_state.uploaded_path, "wb") as f:
            f.write(st.session_state.pdf_bytes)
        st.info("🔄 PDF file re-created for processing.")

    # Continue with normal processing...
    st.markdown("## ⏳ Processing Your Textbook")
    st.markdown("Extracting, embedding and indexing your content.")
    
    progress = st.progress(0)
    status = st.empty()

    # 1️⃣ Set API key
    status.markdown("🔧 Setting OpenAI API key…")
    progress.progress(10)
    os.environ["OPENAI_API_KEY"] = st.session_state.api_key

    # 2️⃣ Init RAG system
    status.markdown("🔧 Initialising RAG system…")
    progress.progress(20)
    rag = RAGSystem()
    time.sleep(0.5)

    # 3️⃣ Ingest PDF
    status.markdown("📄 Reading and chunking PDF…")
    progress.progress(35)
    
    pdf_path = st.session_state.uploaded_path
    rag.ingest_pdf(pdf_path)
    time.sleep(0.5)

    # 4️⃣ Build embeddings
    status.markdown("🧠 Building embeddings…")
    progress.progress(70)
    time.sleep(0.5)

    # 5️⃣ Done!
    status.markdown("✅ Done! You can start chatting.")
    progress.progress(100)

    st.session_state.rag = rag

    # Clean up temporary file
    try:
        os.unlink(pdf_path)
    except Exception as e:
        st.warning(f"Could not delete temp file: {e}")

    time.sleep(1)
    st.session_state.step = 5
    st.rerun()

# -------------------------------------------------
#  PAGE 5 – CHAT INTERFACE WITH HISTORY SIDEBAR
# -------------------------------------------------
def page_chat():
    # Initialize processing flag if it doesn't exist
    if "processing_response" not in st.session_state:
        st.session_state.processing_response = False

    # Get current thread
    current_thread = get_current_thread()

    # Create sidebar for chat history
    with st.sidebar:
        st.markdown("### 💬 Chat History")

        # New chat button
        if st.button("➕ New Chat", key="new_chat_btn", use_container_width=True):
            create_new_thread()
            st.rerun()

        st.markdown("---")

        # Display chat threads (last 10)
        if st.session_state.chat_threads:
            for idx, thread in enumerate(st.session_state.chat_threads[:10]):
                is_current = thread["id"] == st.session_state.current_thread_id

                # Create a container for each thread
                thread_container = st.container()
                with thread_container:
                    col1, col2 = st.columns([5, 1])

                    with col1:
                        # Thread button with highlighting for current thread
                        button_label = f"{'🟢 ' if is_current else ''}{thread['title']}"
                        if st.button(
                            button_label,
                            key=f"thread_{thread['id']}",
                            use_container_width=True,
                            disabled=is_current,
                        ):
                            switch_thread(thread["id"])
                            st.rerun()

                    with col2:
                        # Delete button (small)
                        if st.button("🗑️", key=f"delete_{thread['id']}", help="Delete chat"):
                            delete_thread(thread["id"])
                            st.rerun()

                    # Show timestamp
                    st.caption(format_timestamp(thread["timestamp"]))

                st.markdown("---")
        else:
            st.info("No chat history yet. Start a new conversation!")

        # Settings footer
        st.markdown("---")
        if st.button("⚙️ Settings", key="settings_btn", use_container_width=True):
            st.session_state.step = 3
            st.rerun()

    # Main chat area - Navigation bar
    col_left, col_center, col_right = st.columns([2, 6, 1])

    with col_center:
        st.markdown(
            f"<h4 style='text-align:center; margin:0;'>💬 {current_thread['title']}</h4>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Display messages from current thread
    for msg in current_thread["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Handle new input
    if prompt := st.chat_input("Enter your question…"):
        # Add user message to current thread
        current_thread["messages"].append({"role": "user", "content": prompt})

        # Update thread title if it's the first message
        if len(current_thread["messages"]) == 1:
            update_thread_title(current_thread, prompt)

        # Update timestamp
        current_thread["timestamp"] = datetime.now().isoformat()

        st.session_state.processing_response = True
        st.rerun()

    # Process response if needed
    if (st.session_state.processing_response and
        current_thread["messages"] and
        current_thread["messages"][-1]["role"] == "user"):

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                answer = st.session_state.rag.get_answer(
                    current_thread["messages"][-1]["content"],
                    st.session_state.level
                )
                current_thread["messages"].append({"role": "assistant", "content": answer})
                st.markdown(answer)

        # Reset processing flag
        st.session_state.processing_response = False
        st.rerun()
# -------------------------------------------------
#  MAIN ROUTER
# -------------------------------------------------
def main():
    # Custom CSS for better UI
    st.markdown("""
        <style>
        /* Main container styling */
        .stApp {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }

        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #1e1e2e;
            border-right: 2px solid #4a5568;
        }

        [data-testid="stSidebar"] h3 {
            color: #e2e8f0;
            font-weight: 600;
        }

        [data-testid="stSidebar"] .stButton button {
            background-color: #4a5568;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            transition: all 0.3s ease;
        }

        [data-testid="stSidebar"] .stButton button:hover {
            background-color: #667eea;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        /* Chat message styling */
        .stChatMessage {
            background-color: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 1rem;
            margin: 0.5rem 0;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        /* Button styling */
        .stButton button {
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.3s ease;
        }

        .stButton button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }

        /* Input styling */
        .stTextInput input, .stFileUploader {
            border-radius: 8px;
            border: 2px solid #e2e8f0;
            transition: border-color 0.3s ease;
        }

        .stTextInput input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        /* Progress bar styling */
        .stProgress > div > div {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        }

        /* Radio button styling */
        .stRadio > div {
            background-color: white;
            padding: 1rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        /* File uploader styling */
        [data-testid="stFileUploader"] {
            background-color: white;
            border-radius: 12px;
            padding: 2rem;
            border: 2px dashed #cbd5e0;
        }

        /* Markdown headers */
        h1, h2, h3, h4 {
            color: #2d3748;
            font-weight: 600;
        }

        /* Chat input box */
        .stChatInputContainer {
            border-top: 2px solid #e2e8f0;
            padding-top: 1rem;
        }

        /* Scrollbar styling */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }

        ::-webkit-scrollbar-track {
            background: #f1f5f9;
        }

        ::-webkit-scrollbar-thumb {
            background: #cbd5e0;
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }

        /* Caption (timestamp) styling */
        .caption {
            color: #94a3b8 !important;
            font-size: 0.75rem;
        }
        </style>
    """, unsafe_allow_html=True)

    step = st.session_state.step

    if step == 0:
        page_home()
    elif step == 1:
        page_api_key()
    elif step == 2:
        page_upload()
    elif step == 3:
        page_level()
    elif step == 4:
        page_processing()
    elif step == 5:
        page_chat()
    else:
        st.error("Invalid step – resetting.")
        st.session_state.step = 0
        st.rerun()

if __name__ == "__main__":
    main()