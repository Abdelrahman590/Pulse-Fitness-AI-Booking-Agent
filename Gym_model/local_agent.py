# Local Agent Backend — يشتغل عندك في VS Code
#
# كل حاجة هنا محلية: الـ tools, gym_data, الـ memory, الـ LangGraph graph.
# الحاجة الوحيدة اللي بتتبعت لـ Kaggle هي التوليد نفسه (generate_remote).
#
# pip install langgraph sentence-transformers transformers requests
#
# ملحوظة: محتاجين tokenizer محلي بس (مش الموديل كامل) عشان نعمل apply_chat_template
# قبل ما نبعت الـ prompt الجاهز لـ Kaggle. الـ tokenizer خفيف وبيشتغل على CPU عادي.

import json
import re
import time
from typing import TypedDict, Annotated

import requests
from transformers import AutoTokenizer
from sentence_transformers import SentenceTransformer, util
from langgraph.graph import StateGraph, END

from gym_data import (
    SERVICES, TRAINERS, PACKAGES, GROUP_CLASSES_SCHEDULE,
    booking_system, get_service_price, get_trainers_for_specialty,
)

MODEL_NAME = "Qwen/Qwen3-8B"

# -----------------------------
# إعدادات الاتصال بـ Kaggle — غيّرها هنا كل مرة يتغيّر فيها الـ ngrok URL
# -----------------------------
KAGGLE_SERVER_URL = "ngrok URL"


def set_server_url(url: str):
    """بتتنادى من الـ Streamlit app عشان تحدّث اللينك وقت التشغيل من غير ما تعدّل الملف."""
    global KAGGLE_SERVER_URL
    KAGGLE_SERVER_URL = url.rstrip("/")


def append_messages(left: list, right: list) -> list:
    return left + right


# -----------------------------
# Tokenizer محلي بس (خفيف، بيشتغل على CPU، مش محتاج GPU)
# -----------------------------
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")


def generate_remote(prompt: str, max_new_tokens: int = 1024, temperature: float = 0.3) -> str:
    """الاستدعاء الوحيد اللي بيروح لـ Kaggle — كل حاجة تانية محلية."""
    response = requests.post(
        f"{KAGGLE_SERVER_URL}/generate",
        json={"prompt": prompt, "max_new_tokens": max_new_tokens, "temperature": temperature},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["text"]


class MemoryStore:
    def __init__(self):
        self.entries = []

    def save(self, customer_id: str, fact: str):
        emb = embedder.encode(fact, convert_to_tensor=True)
        self.entries.append({"customer_id": customer_id, "text": fact, "embedding": emb, "timestamp": time.time()})

    def retrieve(self, customer_id: str, query: str, top_k: int = 3, threshold: float = 0.35):
        candidates = [e for e in self.entries if e["customer_id"] == customer_id]
        if not candidates:
            return []
        q_emb = embedder.encode(query, convert_to_tensor=True)
        scored = [(util.cos_sim(q_emb, e["embedding"]).item(), e["text"]) for e in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [t for s, t in scored[:top_k] if s >= threshold]


memory = MemoryStore()


# =====================================================================
# الـ Tools (نفسها بالظبط زي قبل كده — دي جزء من الباك اند المحلي)
# =====================================================================
TOOLS = [
    {"type": "function", "function": {
        "name": "get_service_price",
        "description": "Get the price of a specific gym service, optionally for a given duration/package size.",
        "parameters": {"type": "object", "properties": {
            "service_name": {"type": "string"}, "duration": {"type": "string"},
        }, "required": ["service_name"]},
    }},
    {"type": "function", "function": {
        "name": "get_trainers_for_specialty",
        "description": "List trainers who teach a given specialty.",
        "parameters": {"type": "object", "properties": {"specialty": {"type": "string"}}, "required": ["specialty"]},
    }},
    {"type": "function", "function": {
        "name": "check_availability",
        "description": "Check REAL available time slots for a trainer on a specific date (YYYY-MM-DD). Always call this before confirming any booking.",
        "parameters": {"type": "object", "properties": {
            "trainer": {"type": "string"}, "date": {"type": "string"},
        }, "required": ["trainer", "date"]},
    }},
    {"type": "function", "function": {
        "name": "book_appointment",
        "description": "Book an appointment. Only call AFTER check_availability confirmed the exact slot is free.",
        "parameters": {"type": "object", "properties": {
            "service": {"type": "string"}, "trainer": {"type": "string"},
            "date": {"type": "string"}, "time": {"type": "string"},
        }, "required": ["service", "trainer", "date", "time"]},
    }},
    {"type": "function", "function": {
        "name": "get_group_classes",
        "description": "Get the group classes schedule for a given weekday (English name, e.g. 'Monday').",
        "parameters": {"type": "object", "properties": {"day": {"type": "string"}}, "required": ["day"]},
    }},
    {"type": "function", "function": {
        "name": "get_packages",
        "description": "List all available membership packages.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "retrieve_memory",
        "description": "Retrieve saved facts about this customer relevant to the query.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    }},
    {"type": "function", "function": {
        "name": "save_memory",
        "description": "Save a durable fact about the customer for future conversations.",
        "parameters": {"type": "object", "properties": {"fact": {"type": "string"}}, "required": ["fact"]},
    }},
]


def execute_tool(name: str, args: dict, customer_id: str) -> str:
    if name == "get_service_price":
        price = get_service_price(args["service_name"], args.get("duration"))
        return str(price) if price is not None else "Error: unknown service or duration"
    if name == "get_trainers_for_specialty":
        trainers = get_trainers_for_specialty(args["specialty"])
        return json.dumps(trainers, ensure_ascii=False) if trainers else "No trainers found for this specialty."
    if name == "check_availability":
        slots = booking_system.get_available_slots(args["trainer"], args["date"])
        return json.dumps(slots, ensure_ascii=False) if slots else "No available slots found for this trainer/date."
    if name == "book_appointment":
        result = booking_system.book_slot(
            trainer=args["trainer"], date=args["date"], time=args["time"],
            service=args["service"], customer_id=customer_id,
        )
        return json.dumps(result, ensure_ascii=False)
    if name == "get_group_classes":
        classes = GROUP_CLASSES_SCHEDULE.get(args["day"], [])
        return json.dumps(classes, ensure_ascii=False) if classes else f"No group classes scheduled on {args['day']}."
    if name == "get_packages":
        return json.dumps(PACKAGES, ensure_ascii=False)
    if name == "retrieve_memory":
        results = memory.retrieve(customer_id, args["query"])
        return json.dumps(results, ensure_ascii=False) if results else "No relevant memories found."
    if name == "save_memory":
        memory.save(customer_id, args["fact"])
        return f"Saved: {args['fact']}"
    return f"Error: unknown tool '{name}'"


def strip_thinking(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def extract_tool_calls(text: str):
    matches = re.findall(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", text, re.DOTALL)
    calls = []
    for m in matches:
        try:
            calls.append(json.loads(m))
        except json.JSONDecodeError:
            continue
    return calls


def has_incomplete_tool_call(text: str) -> bool:
    return text.count("<tool_call>") > text.count("</tool_call>")


# =====================================================================
# LangGraph — نفس الـ structure، لكن call_model_node بقى بينادي Kaggle
# =====================================================================
class AgentState(TypedDict):
    messages: Annotated[list, append_messages]
    customer_id: str


def call_model_node(state: AgentState) -> dict:
    prompt = tokenizer.apply_chat_template(
        state["messages"], tools=TOOLS, add_generation_prompt=True,
        tokenize=False, enable_thinking=False,
    )

    try:
        raw = generate_remote(prompt)
    except requests.exceptions.RequestException as e:
        return {"messages": [{"role": "assistant", "content": f"⚠️ مش قادر أوصل لسيرفر الموديل: {e}"}]}

    print(f"\n[agent node output]\n{raw}")

    if has_incomplete_tool_call(raw):
        return {"messages": [{"role": "assistant", "content": "خطأ: الرد اتقطع في نص الطريق."}]}

    return {"messages": [{"role": "assistant", "content": strip_thinking(raw)}]}


def execute_tools_node(state: AgentState) -> dict:
    last_message = state["messages"][-1]["content"]
    calls = extract_tool_calls(last_message)
    if not calls:
        return {}

    call = calls[0]
    name, args = call.get("name"), call.get("arguments", {})
    print(f"[Action] {name}({json.dumps(args, ensure_ascii=False)})")

    result = execute_tool(name, args, state["customer_id"])
    print(f"[Observation] {result}")

    return {"messages": [{"role": "tool", "content": result, "name": name}]}


def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]["content"]
    return "tools" if extract_tool_calls(last_message) else "end"


graph = StateGraph(AgentState)
graph.add_node("agent", call_model_node)
graph.add_node("tools", execute_tools_node)
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
graph.add_edge("tools", "agent")
app_graph = graph.compile()


SYSTEM_PROMPT = """You are the booking assistant for Pulse Fitness, a premium gym in New Cairo (open daily 6:00 AM - 12:00 AM).

Rules:
- NEVER invent prices, availability, or schedules. Always call the relevant tool to get real data.
- Before confirming ANY booking, you MUST call check_availability first to verify the exact slot is free.
- If the requested slot is not available, tell the customer honestly and suggest an alternative from the ones that ARE available.
- Use retrieve_memory when the customer references a past preference. Use save_memory for durable preferences only.
- Respond in Egyptian Arabic, in a friendly, concise customer-service tone.
"""


def run_agent(user_query: str, customer_id: str) -> str:
    initial_state = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query},
        ],
        "customer_id": customer_id,
    }
    final_state = app_graph.invoke(initial_state, config={"recursion_limit": 15})
    return final_state["messages"][-1]["content"]


if __name__ == "__main__":
    # اختبار سريع من الترمينال قبل ما تفتح Streamlit
    print(run_agent("عايز أعرف سعر جلسة اليوجا", "customer_test"))
