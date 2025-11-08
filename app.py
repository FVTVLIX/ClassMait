# app.py
import streamlit as st
from rag_system import RAGSystem
import tempfile
import os

st.title("🧠 AI Learning Assistant")
st.write("Upload a textbook, set your level, and start learning!")

# Initialize session state for the RAG system and chat history
if "rag" not in st.session_state:
    st.session_state.rag = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar for PDF upload and settings
with st.sidebar:
    uploaded_file = st.file_uploader("Upload a Textbook (PDF)", type="pdf")
    user_level = st.selectbox("Select your level", ("Beginner", "Intermediate", "Expert"))
    if uploaded_file is not None:
        if st.button("Process Textbook"):
            with st.spinner('Processing PDF...'):
                # Save uploaded file to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                # Initialize and ingest
                st.session_state.rag = RAGSystem()
                st.session_state.rag.ingest_pdf(tmp_file_path)
                os.unlink(tmp_file_path) # Delete temp file
            st.success("Textbook processed and loaded!")

# Main chat interface
if st.session_state.rag is None:
    st.info("👈 Please upload a PDF textbook to begin.")
else:
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("What is your question?"):
        # Display user message in chat message container
        st.chat_message("user").markdown(prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Get assistant response
        with st.spinner("Thinking..."):
            response = st.session_state.rag.get_answer(prompt, user_level)
        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            st.markdown(response)
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})