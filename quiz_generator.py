# from __future__ import annotations

# from typing import List, Dict

# from dotenv import load_dotenv
# from langchain_community.chat_models import ChatOpenAI
# from langchain_core.messages import HumanMessage, SystemMessage

# load_dotenv()


# def generate_quiz(context: str, user_level: str, num_questions: int = 5) -> List[Dict[str, str]]:
#     """
#     Generate a short quiz tailored to the user's expertise level.

#     Args:
#         context: Reference material that should ground the quiz.
#         user_level: One of "Beginner", "Intermediate", or "Expert".
#         num_questions: The number of question/answer pairs to generate.

#     Returns:
#         A list of dictionaries with "question" and "answer" keys.
#     """
#     cleaned_context = context.strip()
#     if not cleaned_context:
#         return []

#     llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

#     system_prompt = f"""You are an expert tutor creating quizzes for a {user_level} learner.
# Follow these rules:
# - Use only the provided context.
# - Provide concise yet complete answers.
# - Label each item clearly as Q1, Q2, etc.
# - Return exactly {num_questions} items."""

#     user_prompt = f"""Context:
# {cleaned_context}

# Generate {num_questions} question and answer pairs as a JSON array with objects containing "question" and "answer"."""

#     response = llm.invoke(
#         [
#             SystemMessage(content=system_prompt),
#             HumanMessage(content=user_prompt),
#         ]
#     )

#     content = response.content.strip()

#     # Attempt to parse the model output into structured data.
#     try:
#         import json

#         parsed = json.loads(content)
#         if isinstance(parsed, list):
#             normalized: List[Dict[str, str]] = []
#             for item in parsed[:num_questions]:
#                 if not isinstance(item, dict):
#                     continue
#                 question = str(item.get("question", "")).strip()
#                 answer = str(item.get("answer", "")).strip()
#                 if question and answer:
#                     normalized.append({"question": question, "answer": answer})
#             if normalized:
#                 return normalized
#     except json.JSONDecodeError:
#         pass

#     # Fallback: return the raw text in a single entry to avoid silent failure.
#     return [{"question": "Quiz", "answer": content}]


import json
from langchain.schema import HumanMessage, SystemMessage
from langchain.chat_models import ChatOpenAI

# ... [Paste the quiz_function_schema from the previous guide here] ...

def generate_quiz(topic, user_level, context, llm):
    """Generates a quiz JSON object based on the topic and context."""
    
    prompt = f"""Based on the context below, generate a multiple-choice quiz about '{topic}' for a {user_level} level student.

**Relevant Context:**
{context}

**Instructions:**
- Generate 3 questions.
- Each question must have 4 options (A, B, C, D).
- The correct answer must be a single letter (e.g., 'A').
- Provide a clear explanation for the correct answer.
- You MUST call the `generate_quiz` function.
"""
    try:
        llm_with_tools = llm.bind(tools=[quiz_function_schema])
        response = llm_with_tools.invoke([
            SystemMessage(content="You are a helpful quiz generator."),
            HumanMessage(content=prompt)
        ])
        # Extract the JSON arguments from the tool call
        quiz_json_str = response.additional_kwargs['tool_calls'][0]['function']['arguments']
        return json.loads(quiz_json_str)
    except Exception as e:
        print(f"Error generating quiz: {e}")
        return None