# rag_system.py
import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()

class RAGSystem:
    def __init__(self, persist_directory="./chroma_db"):
        self.persist_directory = persist_directory
        self.embeddings = OpenAIEmbeddings()
        self.llm = ChatOpenAI(model='gpt-4', temperature=0.1)
        
        # Try to load existing database, or set to None if it needs to be created
        if os.path.exists(persist_directory):
            self.vector_db = Chroma(persist_directory=persist_directory, embedding_function=self.embeddings)
        else:
            self.vector_db = None

    def ingest_pdf(self, pdf_path):
        """Step 1: Load, split, and store a PDF."""
        print(f"Loading PDF: {pdf_path}")
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        chunks = text_splitter.split_documents(documents)

        self.vector_db = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=self.persist_directory
        )
        # self.vector_db.persist()
        print("PDF processed and stored successfully!")

    def get_answer(self, user_question, user_level):
        """Step 2: Retrieve context and generate an answer."""
        if not self.vector_db:
            return "Error: No knowledge base found. Please ingest a PDF first."

        # Retrieve relevant documents
        retrieved_docs = self.vector_db.similarity_search(user_question, k=3)

        # Create context from retrieved documents
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])

        # The Master Prompt
        system_prompt = f"""You are an expert, empathetic tutor for a university-level course.
The user's current knowledge level is: **{user_level}**.

**CRITICAL GUIDELINES:**
- Answer the user's question based **SOLELY** on the context provided below.
- If the answer is not in the context, say "I'm sorry, that topic isn't covered in my textbook." Do not make up an answer.
- **Tailor your explanation precisely to the user's level:**
  -> **Beginner:** Use simple analogies, avoid jargon, and focus on high-level concepts.
  -> **Intermediate:** Use technical terms but define them briefly. Go into more detail.
  -> **Expert:** Assume deep knowledge. Use advanced terminology and discuss nuances, trade-offs, and complexities.

**CONTEXT FROM THE TEXTBOOK:**
{context}
"""

        # Send the request to the LLM
        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_question)
        ])
        return response.content

# This allows the file to be run directly for ingestion
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "ingest":
        if len(sys.argv) > 2:
            rag = RAGSystem()
            rag.ingest_pdf(sys.argv[2])
        else:
            print("Please provide the path to the PDF file.")