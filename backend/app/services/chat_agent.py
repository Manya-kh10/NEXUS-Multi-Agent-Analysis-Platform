from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import settings
import pandas as pd
import json

llm = ChatGroq(
    api_key=settings.groq_api_key,
    model_name="llama-3.3-70b-versatile"
)

CHART_TYPES = ["bar", "line", "scatter", "histogram", "pie", "box"]

def build_dataset_context(df: pd.DataFrame) -> str:
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    categorical_cols = df.select_dtypes(include='object').columns.tolist()
    sample = df.head(3).to_dict(orient='records')
    return f"""
Dataset Info:
- Shape: {df.shape[0]} rows x {df.shape[1]} columns
- Numeric columns: {numeric_cols}
- Categorical columns: {categorical_cols}
- Sample rows: {sample}
"""

def run_chat_agent(
    user_message: str,
    df: pd.DataFrame,
    chat_history: list
) -> dict:

    context = build_dataset_context(df)
    history_text = ""
    for msg in chat_history[-6:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        history_text += f"{role.upper()}: {content}\n"

    messages = [
        SystemMessage(content=f"""You are a data analysis assistant with access to a dataset.
Answer questions about the data concisely and accurately.
If the user asks for a chart or visualization, respond with JSON in this exact format:
{{
    "type": "chart",
    "chart_type": "bar|line|scatter|histogram|pie|box",
    "x": "column_name",
    "y": "column_name_or_null",
    "title": "chart title",
    "color": "column_name_or_null",
    "explanation": "brief explanation of what this chart shows"
}}
If the user asks a question (not a chart), respond with JSON in this exact format:
{{
    "type": "text",
    "answer": "your answer here",
    "insight": "one key insight from the data"
}}
ALWAYS respond with valid JSON only. No markdown, no extra text.

Dataset Context:
{context}

Previous conversation:
{history_text}
"""),
        HumanMessage(content=user_message)
    ]

    response = llm.invoke(messages)

    try:
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
    except Exception:
        result = {
            "type": "text",
            "answer": response.content,
            "insight": ""
        }

    return result