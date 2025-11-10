quiz_function_schema = {
    "name": "generate_quiz",
    "description": "Generates a multiple choice quiz object based on the discussed topic and user level.",
    "parameters": {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question_text": {"type": "string"},
                        "options": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "correct_answer": {"type": "string", "description": "The letter of the correct option (e.g., 'A')"},
                        "explanation": {"type": "string", "description": "A brief explanation of why the correct answer is right."}
                    },
                    "required": ["question_text", "options", "correct_answer", "explanation"]
                }
            }
        },
        "required": ["questions"]
    }
}

import json
from langchain_core.messages import HumanMessage, SystemMessage
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