# -------------------------------------------------
#  app.py
# -------------------------------------------------
import os
from pydoc import classname
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
    page_title="ClassMait - Your Learning Assistant",
    # page_icon="🧠",
    layout="wide",
    initial_sidebar_state="auto",
)

# -------------------------------------------------
#  Your own RAG wrapper (make sure it works with the API key)
# -------------------------------------------------
from rag_system import (
    RAGSystem,
)  # <-- keep this file unchanged except for optional api_key param
from quiz_generator import generate_quiz, quiz_function_schema
from langchain_openai import ChatOpenAI

# -------------------------------------------------
#  Session‑state defaults (run only once per session)
# -------------------------------------------------
if "step" not in st.session_state:
    st.session_state.step = (
        0  # 0=home, 1=api, 2=upload, 3=level, 4=process, 5=chat, 6=settings
    )

if "api_key" not in st.session_state:
    st.session_state.api_key = ""

if "uploaded_path" not in st.session_state:
    st.session_state.uploaded_path = None  # absolute path string

if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None

if "level" not in st.session_state:
    st.session_state.level = "Beginner"

if "rag" not in st.session_state:
    st.session_state.rag = None

# NEW: Chat history management
if "chat_threads" not in st.session_state:
    st.session_state.chat_threads = (
        []
    )  # list of thread objects: {"id": str, "title": str, "timestamp": str, "messages": []}

if "current_thread_id" not in st.session_state:
    st.session_state.current_thread_id = None

# DEPRECATED: Keep for backward compatibility, but we'll use chat_threads now
if "messages" not in st.session_state:
    st.session_state.messages = (
        []
    )  # list of dicts: {"role": "user"/"assistant", "content": "..."}

# Quiz state management
if "current_quiz" not in st.session_state:
    st.session_state.current_quiz = None  # stores quiz data

if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {}  # user's selected answers

if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False  # whether quiz has been submitted


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
#  Session Persistence Helper Functions
# -------------------------------------------------
SESSION_FILE = "session_state.json"


def save_session_state():
    """Saves important session state to a JSON file."""
    try:
        state_to_save = {
            "api_key": st.session_state.get("api_key", ""),
            "level": st.session_state.get("level", "Beginner"),
            "chat_threads": st.session_state.get("chat_threads", []),
            "current_thread_id": st.session_state.get("current_thread_id", None),
            "step": st.session_state.get("step", 0),
            "pdf_bytes": None,  # Don't save PDF bytes - too large
            "uploaded_path": None,  # Don't save temp paths
            "rag_initialized": st.session_state.rag
            is not None,  # Track if RAG was set up
        }

        with open(SESSION_FILE, "w") as f:
            json.dump(state_to_save, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving session state: {e}")
        return False


def load_session_state():
    """Loads session state from JSON file if it exists."""
    if not Path(SESSION_FILE).exists():
        return False

    try:
        with open(SESSION_FILE, "r") as f:
            saved_state = json.load(f)

        # Only load if we're at the initial state
        if st.session_state.step == 0 and not st.session_state.api_key:
            st.session_state.api_key = saved_state.get("api_key", "")
            st.session_state.level = saved_state.get("level", "Beginner")
            st.session_state.chat_threads = saved_state.get("chat_threads", [])
            st.session_state.current_thread_id = saved_state.get(
                "current_thread_id", None
            )

            # If we have an API key and chat history, skip to chat page
            # BUT only if RAG was initialized (otherwise go to upload page)
            if st.session_state.api_key:
                # Set environment variable
                os.environ["OPENAI_API_KEY"] = st.session_state.api_key

                # Check if RAG was previously initialized
                if saved_state.get("rag_initialized", False):
                    # RAG was initialized before but is lost on refresh
                    # Go to settings page so user can re-upload PDF
                    st.session_state.step = 3
                elif st.session_state.chat_threads:
                    # Has chat threads but no RAG - go to settings
                    st.session_state.step = 3
                else:
                    # Fresh start with just API key - go to upload
                    st.session_state.step = 2

        return True
    except Exception as e:
        print(f"Error loading session state: {e}")
        return False


def load_api_key_from_secrets():
    """Loads API key from Streamlit secrets if available."""
    try:
        if hasattr(st, "secrets") and "OPENAI_API_KEY" in st.secrets:
            api_key = st.secrets["OPENAI_API_KEY"]
            if api_key and api_key != "sk-your-api-key-here":
                st.session_state.api_key = api_key
                os.environ["OPENAI_API_KEY"] = api_key
                return True
    except Exception as e:
        pass
    return False


def clear_session_data():
    """Clears saved session data."""
    try:
        if Path(SESSION_FILE).exists():
            os.remove(SESSION_FILE)
        return True
    except Exception as e:
        print(f"Error clearing session data: {e}")
        return False


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
        "messages": [],
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
    st.session_state.chat_threads = [
        t for t in st.session_state.chat_threads if t["id"] != thread_id
    ]

    # If we deleted the current thread, create a new one
    if st.session_state.current_thread_id == thread_id:
        if st.session_state.chat_threads:
            st.session_state.current_thread_id = st.session_state.chat_threads[0]["id"]
        else:
            create_new_thread()


def update_thread_title(thread, first_message):
    """Updates thread title based on first message (truncate to 30 chars)."""
    if thread["title"] == "New Conversation" and first_message:
        thread["title"] = (
            first_message[:30] + "..." if len(first_message) > 30 else first_message
        )


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
    col_left, col_center, col_right = st.columns([1, 5, 1])

    # ← Back button (disabled on the very first step)
    with col_left:
        if st.session_state.step > 0:
            if st.button("← Back", key="nav_back"):
                st.session_state.step -= 1
                st.rerun()
        else:
            st.write("")  # placeholder for layout symmetry

    # Step indicator (center)
    with col_center:
        st.markdown(
            f"<h4 class='step-indicator'>Step {st.session_state.step + 1} of 6</h4>",
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

    # Try to load API key from secrets on first load
    if not st.session_state.api_key:
        load_api_key_from_secrets()

    # Try to load saved session state on first load
    if "session_loaded" not in st.session_state:
        st.session_state.session_loaded = True
        if load_session_state():
            # If we successfully loaded a previous session with API key, skip ahead
            if st.session_state.api_key and st.session_state.step > 0:
                st.rerun()

    st.markdown(
        """
        <div class="home-container">
            <h1 class="title">CLASSM<span class="italic">ai</span>T</h1>
            <p class="subtitle">Your Personal AI Learning Assistant</p>
            <p class="home-description">
                Transform any textbook into an interactive learning experience
                with personalized explanations and quizzes.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Centered "Get Started" button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Get Started →", key="home_start", use_container_width=True):
            st.session_state.step = 1  # move to API‑key page
            st.rerun()


# -------------------------------------------------
#  PAGE 1 – API KEY
# -------------------------------------------------
def page_api_key():
    nav_bar()

    # Check for API key from secrets
    if not st.session_state.api_key:
        if load_api_key_from_secrets():
            st.success("API key loaded from secrets.toml!")

    st.markdown(
        """
        <div class="api-key-container">
            <h2 class="api-key-title">OpenAI API Key</h2>
            <p class="api-key-description">Enter your OpenAI API key so the assistant can call GPT‑4.</p>
            <p class="api-key-description-link">You can create a key at
            <a href="https://platform.openai.com/account/api-keys" target="_blank">
            platform.openai.com/account/api-keys</a>.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Show info about using secrets.toml
    with st.expander("Tip: Save your API key permanently!"):
        st.markdown(
            """
            To avoid re-entering your API key every time:
            1. Open `.streamlit/secrets.toml` in your project directory
            2. Uncomment the `OPENAI_API_KEY` line
            3. Replace `"sk-your-api-key-here"` with your actual API key
            4. Save the file and restart the app
            Your API key will be automatically loaded on startup!
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="api-key-below">
        <p>Enter your API key below to continue.</p>
        </div>
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
        os.environ["OPENAI_API_KEY"] = (
            api_key  # needed for OpenAIEmbeddings / ChatOpenAI
        )

    # Forward button (disabled until a key is entered)
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        if st.button(
            "Continue →",
            key="api_continue",
            disabled=not api_key,
            use_container_width=True,
        ):
            save_session_state()  # Save progress
            st.session_state.step = 2  # go to upload page
            st.rerun()


# -------------------------------------------------
#  PAGE 2 – UPLOAD PDF
# -------------------------------------------------
def page_upload():
    nav_bar()

    st.markdown(
        """
        <div class="upload-container">
            <h2 class="upload-title">Upload Your Textbook (PDF)</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
    col_left, col_center, col_right = st.columns([1, 2, 1])
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

    # Show warning if RAG is not initialized (e.g., after page refresh)
    # if st.session_state.rag is None:
    #     st.warning(
    #         """
    #         ⚠️ **Notice:** Your textbook will need to be re-processed if you refresh this page.

    #         Please upload your PDF again to continue chatting if page has been refreshed. Your chat history has been preserved!
    #         """
    #     )
    #     col_left, col_center, col_right = st.columns([1, 2, 1])
    #     with col_center:
    #         if st.button("Upload New Textbook →", use_container_width=True, type="primary"):
    #             st.session_state.step = 2
    #             st.rerun()
    #         st.markdown("---")

    st.markdown(""" 
    <div class="level-container">
        <h2 class="level-title">Choose Your Learning Level</h2>
        <p class="level-description">Select your learning level to help the assistant tailor their responses to your knowledge level. This will help the assistant provide more accurate and helpful responses. You can change your level at any time.</p> 
    </div>
    """,
    unsafe_allow_html=True,
    )


    level = st.radio(
        "Select level:",
        ("Beginner", "Intermediate", "Expert"),
        index=("Beginner", "Intermediate", "Expert").index(st.session_state.level),
        key="level_radio",
    )
    st.session_state.level = level

    st.markdown("---")

    # Show different buttons based on RAG status
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        # If RAG exists, allow going to chat
        if st.session_state.rag is not None:
            if st.button(
                "Continue to Chat →",
                key="goto_chat",
                use_container_width=True,
                type="primary",
            ):
                save_session_state()
                st.session_state.step = 5
                st.rerun()
        # Otherwise, need to process textbook
        elif st.session_state.uploaded_path or st.session_state.pdf_bytes:
            if st.button(
                "Process Textbook", key="process_start", use_container_width=True
            ):
                save_session_state()  # Save before processing
                st.session_state.step = 4  # go to processing page
                st.rerun()
        else:
            if st.button(
                "Upload Textbook", key="goto_upload", use_container_width=True
            ):
                st.session_state.step = 2
                st.rerun()


# -------------------------------------------------
#  PAGE 4 – PROCESSING 
# -------------------------------------------------
def page_processing():
    # nav_bar()

    # # Initialize processing state
    # if "processing_stage" not in st.session_state:
    #     st.session_state.processing_stage = 0  # 0=initialized, 1=processing, 2=done, 3=stopped
    
    # # Main container to isolate the page
    # with st.container():
    #     # Navigation bar at top
    #     col_left, col_center, col_right = st.columns([1, 6, 1])
    #     with col_left:
    #         st.button("← Back", key="processing_back", 
    #                   on_click=lambda: st.session_state.update({"step": 3}))
        
    #     # Title
    #     st.markdown("## ⏳ Processing Your Textbook")
    #     st.markdown("Please wait while we analyze your textbook. This may take several minutes.")
        
    #     # Progress section
    #     with st.container():
    #         if st.session_state.processing_stage == 0:  # Initial state
    #             st.session_state.processing_stage = 1  # Start processing
    #             st.rerun()
            
    #         # Progress bar
    #         progress_bar = st.progress(0)
            
    #         # Status display
    #         status_text = st.empty()
            
    #         # Stop button container
    #         stop_container = st.empty()
            
    #         # Initialize progress value
    #         if "processing_progress" not in st.session_state:
    #             st.session_state.processing_progress = 0
            
    #         # Simulation steps (replace with actual steps in your implementation)
    #         processing_steps = [
    #             ("Initializing learning system...", 10),
    #             ("Analyzing textbook content...", 30),
    #             ("Extracting key concepts...", 50),
    #             ("Building knowledge structure...", 70),
    #             ("Finalizing content indexing...", 90),
    #             ("Processing completed successfully!", 100)
    #         ]
            
    #         # If we're processing (stage 1) and not finished
    #         if st.session_state.processing_stage == 1:
    #             # Get current step based on progress
    #             current_step = None
    #             for step in processing_steps:
    #                 if st.session_state.processing_progress <= step[1]:
    #                     current_step = step
    #                     break
                
    #             if current_step:
    #                 # Update status and progress
    #                 status_text.markdown(f"**{current_step[0]}**")
    #                 progress_bar.progress(st.session_state.processing_progress)
                    
    #                 # Update progress
    #                 st.session_state.processing_progress += 1
                    
    #                 # Add Stop button
    #                 if stop_container.button("Stop Processing", key="stop_button"):
    #                     st.session_state.processing_stage = 3  # Stopped
    #                     st.rerun()
                    
    #                 # Rerun every 0.1 seconds to simulate progress
    #                 time.sleep(0.05)
    #                 st.rerun()
    #             else:
    #                 st.session_state.processing_stage = 2
    #                 st.rerun()
            
    #         # When processing completes
    #         elif st.session_state.processing_stage == 2:
    #             progress_bar.progress(100)
    #             status_text.markdown("Processing completed successfully!")
    #             time.sleep(1)  # Show completion briefly
                
    #             # Actual RAG processing
    #             try:
    #                 st.session_state.rag = RAGSystem()
    #                 st.session_state.rag.ingest_pdf(st.session_state.uploaded_path)
                    
    #                 # Clean up temporary file
    #                 try:
    #                     os.unlink(st.session_state.uploaded_path)
    #                 except Exception as e:
    #                     st.warning(f"Could not delete temporary file: {e}")
    #             except Exception as e:
    #                 status_text.error(f"Error during processing: {e}")
    #                 time.sleep(1)
    #                 st.session_state.step = 3
    #                 st.rerun()
                
    #             # Move to chat page
    #             st.session_state.step = 5
    #             st.rerun()
            
    #         # When processing is stopped
    #         elif st.session_state.processing_stage == 3:
    #             progress_bar.progress(st.session_state.processing_progress)
    #             status_text.error("Processing stopped")
                
    #             # Option to resume or go back
    #             if st.button("↩ Continue Processing", key="resume_processing"):
    #                 st.session_state.processing_stage = 1
    #                 st.rerun()
                
    #             if st.button("← Back to Settings", key="processing_stop_back"):
    #                 st.session_state.step = 3
    #                 st.rerun()


    # Initialize cancel flag if it doesn't exist
    if "cancel_processing" not in st.session_state:
        st.session_state.cancel_processing = False

    # Wrap entire processing page in a container div for isolation
    # st.markdown(
    #     """
    #     <div id="processing-page-container" style="width:100%; min-height:100vh; background:#fff; position:relative; z-index:1000;">
    #     </div>
    #     """,
    #     unsafe_allow_html=True,
    # )

    # Custom navigation bar for processing page (no back button, only stop button)
    # st.markdown('<div id="processing-nav-bar" class="processing-navigation">', unsafe_allow_html=True)

    col_left, col_center, col_right = st.columns([1, 6, 1])

    with col_left:
        st.button("← Back", key="processing_back", 
        on_click=lambda: st.session_state.update({"step": 3}))

    with col_center:
        st.markdown(
            f'<div id="processing-step-indicator"><h4 style="text-align:center; margin:0;">Step {st.session_state.step + 1} of 6</h4></div>',
            unsafe_allow_html=True,
        )

    with col_right:
        st.markdown('<div id="processing-stop-button-container">', unsafe_allow_html=True)
        if st.button("⏹ Stop", key="stop_processing", type="secondary"):
            st.session_state.cancel_processing = True
            # Clean up and go back to upload step
            if st.session_state.uploaded_path and Path(st.session_state.uploaded_path).is_file():
                try:
                    os.unlink(st.session_state.uploaded_path)
                except:
                    pass
            st.session_state.step = 2
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # st.markdown('</div>', unsafe_allow_html=True)  # Close processing-nav-bar
    # st.markdown("---")

    # Check if user cancelled
    if st.session_state.cancel_processing:
        st.session_state.cancel_processing = False
        return

    # NEW: Re-create PDF file if it was deleted
    if (st.session_state.uploaded_path and
        not Path(st.session_state.uploaded_path).is_file()):
        # File was deleted, re-create it from stored bytes
        with open(st.session_state.uploaded_path, "wb") as f:
            f.write(st.session_state.pdf_bytes)
        st.info("🔄 PDF file re-created for processing.")

        # Title section
    st.markdown(
        '<div id="processing-title-section">'
        '<h2>Processing Your Textbook</h2>'
        '<p>Extracting, embedding and indexing your content.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Processing content wrapper
    st.markdown('<div id="processing-content-container" class="processing-content">', unsafe_allow_html=True)

    # Progress section wrapper
    st.markdown('<div id="processing-progress-section" class="progress-section">', unsafe_allow_html=True)

    progress = st.progress(0)
    st.markdown('<div id="processing-status-container" class="status-container">', unsafe_allow_html=True)
    status = st.empty()
    st.markdown('</div>', unsafe_allow_html=True)

    # 1️⃣ Set API key
    status.markdown('<div class="status-message">Setting OpenAI API key…</div>', unsafe_allow_html=True)
    progress.progress(10)
    os.environ["OPENAI_API_KEY"] = st.session_state.api_key

    # 2️⃣ Init RAG system
    status.markdown('<div class="status-message">Initialising RAG system…</div>', unsafe_allow_html=True)
    progress.progress(20)
    rag = RAGSystem()
    time.sleep(0.5)

    # 3️⃣ Ingest PDF
    status.markdown('<div class="status-message">Reading and chunking PDF…</div>', unsafe_allow_html=True)
    progress.progress(35)

    pdf_path = st.session_state.uploaded_path
    rag.ingest_pdf(pdf_path)
    time.sleep(0.5)

    # 4️⃣ Build embeddings
    status.markdown('<div class="status-message">Building embeddings…</div>', unsafe_allow_html=True)
    progress.progress(70)
    time.sleep(0.5)

    # 5️⃣ Done!
    status.markdown('<div class="status-message">Done! You can start chatting.</div>', unsafe_allow_html=True)
    progress.progress(100)

    st.markdown('</div>', unsafe_allow_html=True)  # Close processing-progress-section
    st.markdown('</div>', unsafe_allow_html=True)  # Close processing-content-container

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

    # Add mobile menu toggle button and JavaScript
    st.markdown("""
        <button class="mobile-menu-toggle" onclick="toggleMobileMenu()">
            ☰ Menu
        </button>
        <div class="mobile-menu-overlay" onclick="toggleMobileMenu()"></div>
        <script>
        function toggleMobileMenu() {
            const sidebar = window.parent.document.querySelector('[data-testid="stSidebar"]');
            const overlay = window.parent.document.querySelector('.mobile-menu-overlay');
            if (sidebar && overlay) {
                sidebar.classList.toggle('mobile-menu-open');
                overlay.classList.toggle('active');
            }
        }
        </script>
    """, unsafe_allow_html=True)

    # CHECK: Ensure RAG system is initialized before allowing chat
    if st.session_state.rag is None:
        st.error("**PDF Processing Required**")
        st.warning(
            """
            Your textbook needs to be processed before you can chat.

            This happens when:
            - You refresh the page (the RAG system needs to be reloaded)
            - You haven't uploaded a PDF yet
            - The session was restored from a previous visit

            **Please upload and process your textbook to continue.**
            """
        )

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button(
                "Go to Upload & Process", use_container_width=True, type="primary"
            ):
                st.session_state.step = 2
                st.rerun()

        st.info(
            "**Tip:** Your chat history has been preserved and will be available after processing."
        )
        st.stop()  # Stop execution here to prevent the error

    # Get current thread
    current_thread = get_current_thread()

    # Create sidebar for chat history
    with st.sidebar:
        st.markdown("### Chat History")

        # New chat button
        if st.button("➕  New Chat", key="new_chat_btn", use_container_width=True):
            create_new_thread()
            save_session_state()  # Save after creating new thread
            st.rerun()

        st.markdown("---")

        # Display chat threads (last 10)
        if st.session_state.chat_threads:
            for idx, thread in enumerate(st.session_state.chat_threads[:10]):
                is_current = thread["id"] == st.session_state.current_thread_id

                # Create a container for each thread
                thread_container = st.container()
                with thread_container:
                    col1, col2 = st.columns([8, 1])

                    with col1:
                        # Thread button with highlighting for current thread
                        button_label = f"{'🟢  ' if is_current else ''}{thread['title']}"
                        if st.button(
                            button_label,
                            key=f"thread_{thread['id']}",
                            use_container_width=True,
                            disabled=is_current,
                        ):
                            switch_thread(thread["id"])
                            save_session_state()  # Save after switching
                            st.rerun()

                    with col2:
                        # Delete button (small)
                        if st.button(
                            "X", key=f"delete_{thread['id']}", help="Delete chat"
                        ):
                            delete_thread(thread["id"])
                            save_session_state()  # Save after deleting
                            st.rerun()

                    # Show timestamp with smaller font
                    st.markdown(
                        f"<p style='color: #94a3b8; font-size: 0.75rem; margin-top: -0.5rem;'>{format_timestamp(thread['timestamp'])}</p>",
                        unsafe_allow_html=True,
                    )

                # st.markdown("---")
        else:
            st.info("No chat history yet. Start a new conversation!")

        # Settings footer
        st.markdown("---")
        if st.button("Settings", key="settings_btn", use_container_width=True):
            st.session_state.step = 6
            st.rerun()

    # Main chat area - Navigation bar
    col_left, col_center, col_right = st.columns([2, 6, 1])

    with col_center:
        st.markdown(
            f"<h4 class='chat-title'>{current_thread['title']}</h4>",
            unsafe_allow_html=True,
        )

    # st.markdown("---")

    # Quiz Generation Section
    with st.expander("📝 Generate Quiz", expanded=st.session_state.current_quiz is not None):
        st.markdown("Generate a quiz based on the topics discussed or from your textbook!")

        col1, col2 = st.columns([3, 1])

        with col1:
            quiz_topic = st.text_input(
                "Enter a topic for the quiz (or leave blank to use recent conversation)",
                placeholder="e.g., 'photosynthesis' or 'calculus derivatives'",
                key="quiz_topic_input"
            )

        with col2:
            if st.button("Generate Quiz", key="generate_quiz_btn", type="primary", use_container_width=True):
                # Determine topic and context
                topic = quiz_topic if quiz_topic else "recent discussion"

                # Get context from recent messages or RAG system
                context = ""
                if current_thread["messages"]:
                    # Use last few messages as context
                    recent_messages = current_thread["messages"][-4:]
                    context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])
                else:
                    # Use RAG system to get context
                    if quiz_topic:
                        retrieved_docs = st.session_state.rag.vector_db.similarity_search(quiz_topic, k=3)
                        context = "\n".join([doc.page_content for doc in retrieved_docs])

                # Generate quiz
                with st.spinner("Generating quiz..."):
                    llm = ChatOpenAI(model="gpt-4", temperature=0.1)
                    quiz_data = generate_quiz(topic, st.session_state.level, context, llm)

                    if quiz_data:
                        st.session_state.current_quiz = quiz_data
                        st.session_state.quiz_answers = {}
                        st.session_state.quiz_submitted = False
                        st.success("Quiz generated! Answer the questions below.")
                        st.rerun()
                    else:
                        st.error("Failed to generate quiz. Please try again.")

        # Display quiz if one exists
        if st.session_state.current_quiz:
            st.markdown("---")
            st.markdown("### Your Quiz")

            quiz = st.session_state.current_quiz

            # Display each question
            for idx, question in enumerate(quiz.get("questions", [])):
                st.markdown(f"**Question {idx + 1}:** {question['question_text']}")

                # Radio buttons for options
                selected = st.radio(
                    "Select your answer:",
                    options=["A", "B", "C", "D"],
                    format_func=lambda x: f"{x}. {question['options'][ord(x) - ord('A')]}",
                    key=f"quiz_q_{idx}",
                    index=None if f"q_{idx}" not in st.session_state.quiz_answers else ["A", "B", "C", "D"].index(st.session_state.quiz_answers[f"q_{idx}"])
                )

                if selected:
                    st.session_state.quiz_answers[f"q_{idx}"] = selected

                # Show explanation if quiz is submitted
                if st.session_state.quiz_submitted:
                    correct = question['correct_answer']
                    user_answer = st.session_state.quiz_answers.get(f"q_{idx}", None)

                    if user_answer == correct:
                        st.success(f"✅ Correct! The answer is {correct}.")
                    else:
                        st.error(f"❌ Incorrect. You selected {user_answer}. The correct answer is {correct}.")

                    st.info(f"**Explanation:** {question['explanation']}")

                st.markdown("---")

            # Submit/Reset buttons
            col1, col2, col3 = st.columns([1, 1, 1])

            with col1:
                if not st.session_state.quiz_submitted:
                    if st.button("Submit Quiz", key="submit_quiz_btn", type="primary", use_container_width=True):
                        if len(st.session_state.quiz_answers) == len(quiz.get("questions", [])):
                            st.session_state.quiz_submitted = True
                            st.rerun()
                        else:
                            st.warning("Please answer all questions before submitting!")

            with col2:
                if st.session_state.quiz_submitted:
                    # Calculate score
                    correct_count = 0
                    total_questions = len(quiz.get("questions", []))

                    for idx, question in enumerate(quiz.get("questions", [])):
                        if st.session_state.quiz_answers.get(f"q_{idx}") == question['correct_answer']:
                            correct_count += 1

                    score_percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0
                    st.metric("Your Score", f"{correct_count}/{total_questions}", f"{score_percentage:.0f}%")

            with col3:
                if st.button("New Quiz", key="new_quiz_btn", use_container_width=True):
                    st.session_state.current_quiz = None
                    st.session_state.quiz_answers = {}
                    st.session_state.quiz_submitted = False
                    st.rerun()

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

        # Auto-save session state
        save_session_state()

        st.session_state.processing_response = True
        st.rerun()

    # Process response if needed
    if (
        st.session_state.processing_response
        and current_thread["messages"]
        and current_thread["messages"][-1]["role"] == "user"
    ):

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                answer = st.session_state.rag.get_answer(
                    current_thread["messages"][-1]["content"], st.session_state.level
                )
                current_thread["messages"].append(
                    {"role": "assistant", "content": answer}
                )
                st.markdown(answer)

        # Auto-save after getting response
        save_session_state()

        # Reset processing flag
        st.session_state.processing_response = False
        st.rerun()


# -------------------------------------------------
#  PAGE 6 – SETTINGS PAGE
# -------------------------------------------------
def page_settings():
    # Initialize confirmation flag
    if "confirm_clear" not in st.session_state:
        st.session_state.confirm_clear = False

    st.markdown(
        "<h2 class='settings-title'>Settings & Management</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center;'>Manage your API key, sessions, and textbooks</p>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # Section 1: API Key Management
    st.markdown(
        "<h3 class='settings-subtitle'>API Key Management</h3>",
        unsafe_allow_html=True,
    )

    # col1, col2 = st.columns([2, 1])
    # with col1:
    #     current_key = st.session_state.get("api_key", "")
    #     display_key = current_key[:15] + "..." if len(current_key) > 15 else current_key
    #     if current_key:
    #         st.info(f"**Current API Key:** `{display_key}`")
    #     else:
    #         st.warning("**No API key set**")

    # with col2:
    #     if current_key and st.button("Remove Key", use_container_width=True):
    #         st.session_state.api_key = ""
    #         if "OPENAI_API_KEY" in os.environ:
    #             del os.environ["OPENAI_API_KEY"]
    #         save_session_state()
    #         st.success("API key removed!")
    #         time.sleep(1)
    #         st.rerun()

    current_key = st.session_state.get("api_key", "")
    display_key = current_key[:15] + "..." if len(current_key) > 15 else current_key
    if current_key:
        st.info(f"**Current API Key:** `{display_key}`")
    else:
        st.warning("**No API key set**")



    # Update API key
    with st.expander("Update API Key"):
        new_api_key = st.text_input(
            "Enter new API key",
            type="password",
            placeholder="sk-...",
            key="new_api_key_input",
        )
        if st.button("Update API Key", type="primary"):
            if new_api_key:
                st.session_state.api_key = new_api_key
                os.environ["OPENAI_API_KEY"] = new_api_key
                save_session_state()
                st.success("API key updated successfully!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Please enter a valid API key")

    if current_key and st.button("Remove Key", use_container_width=True):
        st.session_state.api_key = ""
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        save_session_state()
        st.success("API key removed!")
        time.sleep(1)
        st.rerun()

    st.markdown("---")

    # Section 2: PDF Management
    st.markdown(
        "<h3 class='settings-subtitle'>Textbook Management</h3>",
        unsafe_allow_html=True,
    )

    rag_status = (
        "**Loaded**" if st.session_state.rag is not None else "**Not Loaded**"
    )
    st.info(f"RAG System Status: {rag_status}")

    # col1, col2 = st.columns(2)
    # with col1:
    #     if st.button("📤 Upload New PDF", use_container_width=True, type="primary"):
    #         st.session_state.step = 2
    #         st.rerun()

    # with col2:
    #     if st.session_state.rag is not None:
    #         st.success("PDF is processed and ready")
    #     else:
    #         st.warning("No PDF loaded")

    if st.session_state.rag is not None:
        st.success("PDF is processed and ready")
    else:
        st.warning("No PDF loaded")

    if st.button("Upload New PDF", use_container_width=True, type="primary"):
        st.session_state.step = 2
        st.rerun()

    st.markdown("---")

    # Section 3: Session Management
    st.markdown(
        "<h3 class='settings-subtitle'>Session Management</h3>",
        unsafe_allow_html=True,
    )

    # Show session info
    session_info = f"""
    - **Chat Threads:** {len(st.session_state.get('chat_threads', []))}
    - **Current Level:** {st.session_state.get('level', 'Beginner')}
    - **API Key Set:** {'Yes' if st.session_state.get('api_key') else 'No'}
    """
    st.info(session_info)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Save Session", use_container_width=True):
            if save_session_state():
                st.success("Session saved successfully!")
                time.sleep(1)
            else:
                st.error("Failed to save session")

    with col2:
        if not st.session_state.confirm_clear:
            if st.button(
                "Clear All Data", use_container_width=True, type="secondary"
            ):
                st.session_state.confirm_clear = True
                st.rerun()
        else:
            # Show confirmation buttons
            st.warning("Are you sure? This will delete everything!")
            col_yes, col_no = st.columns(2)

            with col_yes:
                if st.button(
                    "Yes, Clear All", use_container_width=True, type="primary"
                ):
                    # Clear the session file
                    clear_session_data()

                    # Reset session state keys
                    keys_to_clear = [
                        "chat_threads",
                        "current_thread_id",
                        "api_key",
                        "rag",
                        "uploaded_path",
                        "pdf_bytes",
                        "confirm_clear",
                        "messages",
                    ]
                    for key in keys_to_clear:
                        if key in st.session_state:
                            st.session_state[key] = (
                                [] if key in ["chat_threads", "messages"] else None
                            )

                    st.success("All data cleared!")
                    time.sleep(1)
                    st.session_state.step = 0
                    st.rerun()

            with col_no:
                if st.button("Cancel", use_container_width=True, type="secondary"):
                    st.session_state.confirm_clear = False
                    st.rerun()

    st.markdown("---")

    # Section 4: Learning Level
    st.markdown(
        "<h3 class='settings-subtitle'>Learning Level</h3>", unsafe_allow_html=True
    )

    level = st.radio(
        "Select your preferred difficulty level:",
        ("Beginner", "Intermediate", "Expert"),
        index=("Beginner", "Intermediate", "Expert").index(st.session_state.level),
        key="settings_level_radio",
        horizontal=True,
    )

    if level != st.session_state.level:
        st.session_state.level = level
        save_session_state()
        st.success(f"Level updated to {level}")

    st.markdown("---")

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.session_state.rag is not None:
            if st.button(
                "Continue to Chat", use_container_width=True, type="primary"
            ):
                st.session_state.step = 5
                st.rerun()
        else:
            st.warning("⚠️ Please upload and process a PDF before chatting")
            if st.button("Go to Upload", use_container_width=True, type="primary"):
                st.session_state.step = 2
                st.rerun()


# -------------------------------------------------
#  MAIN ROUTER
# -------------------------------------------------
def main():
    # Load custom CSS from external file
    css_file = Path(".streamlit/style.css")
    if css_file.exists():
        with open(css_file) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning("Custom CSS file not found. Using default styles.")

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
    elif step == 6:
        page_settings()
    else:
        st.error("Invalid step – resetting.")
        st.session_state.step = 0
        st.rerun()


if __name__ == "__main__":
    main()
