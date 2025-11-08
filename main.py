# main.py
from rag_system import RAGSystem
from quiz_generator import generate_quiz  # We'll create this next
from dotenv import load_dotenv

load_dotenv()

def main():
    # Initialize the RAG system
    rag = RAGSystem()
    
    print("Welcome to your Personal Learning Assistant!")
    
    # Check if we need to ingest a PDF
    # In a real app, you'd handle this more gracefully
    if rag.vector_db is None:
        pdf_path = input("No knowledge base found. Enter path to PDF to ingest: ")
        rag.ingest_pdf(pdf_path)
    
    user_level = input("Enter your expertise level (Beginner/Intermediate/Expert): ").capitalize()
    conversation_history = []

    while True:
        user_question = input("\nWhat is your question? (type 'quit' to exit): ")
        if user_question.lower() == 'quit':
            break

        # Get answer from RAG system
        answer = rag.get_answer(user_question, user_level)
        print(f"\nTutor: {answer}")

        # Store conversation
        conversation_history.append(f"User: {user_question}")
        conversation_history.append(f"Tutor: {answer}")

if __name__ == "__main__":
    main()