# 🏋️ Pulse Fitness — AI Booking Agent

An intelligent booking system built on a **ReAct Agent** powered by an open-source model (Qwen3-8B). It handles gym customer interactions (Pulse Fitness) through natural Arabic conversation — showing services and prices, checking real appointment availability, and executing bookings — without ever "inventing" information.

---

## 📐 Architecture

The system is split into two fully decoupled layers: the **model** (running on cloud GPU) and **all business logic** (running locally), connected through a secure tunnel (ngrok).

```
┌───────────────────────────────┐            ┌──────────────────────────────────┐
│         Kaggle (GPU)           │            │         Your Machine (local)       │
│                                 │            │                                    │
│  kaggle_generate_server.py     │   ngrok    │  streamlit_app.py   (UI)          │
│  • Loads Qwen3-8B (4-bit)      │◄──HTTP────►│  local_agent.py     (Agent)       │
│  • Single endpoint: /generate  │            │  gym_data.py         (Data)       │
│  • No business logic here      │            │  • Tools                          │
│                                 │            │  • LangGraph orchestration         │
│                                 │            │  • Long-term Memory                │
└───────────────────────────────┘            └──────────────────────────────────┘
```

**Why this architecture?**
- The model needs a GPU — it runs on Kaggle (free) instead of requiring a powerful GPU on your own machine.
- Business logic (pricing, booking, tools) stays local, simple to trace and modify, and fully independent of any specific model — you can swap the model without touching the booking logic at all.
- Only raw text crosses the network (prompt ↔ generated text) — no business logic ever passes through it.

---

## 📁 File Structure

| File | Description | Runs on |
|---|---|---|
| `kaggle_generate_server.py` | Minimal generation server (FastAPI) that wraps the model and exposes it via ngrok | Kaggle |
| `gym_data.py` | Data layer: services, prices, trainers, class schedules, and the actual booking logic (source of truth) | Local |
| `local_agent.py` | The full ReAct Agent: Tools, Memory, and LangGraph orchestration | Local |
| `streamlit_app.py` | Chat interface | Local |
| `requirements.txt` | Local backend dependencies | Local |
| `setup_env.sh` / `setup_env.ps1` | Virtual environment setup scripts (macOS/Linux and Windows) | Local |

---

## ✨ Features

- **ReAct Loop**: The agent decides on its own when to use a tool versus respond directly (Thought → Action → Observation).
- **Grounded Responses**: The model is not allowed to invent prices or availability — every piece of information must come from a real tool call backed by `gym_data.py`.
- **Hard Availability Constraints**: Slot availability checks and booking execution happen in plain code (`BookingSystem.book_slot`), not the model's guesswork — so double-booking an already-taken slot is impossible.
- **Long-term Memory**: Customer preferences (e.g. prefers mornings, avoids a certain day) are stored as embeddings and automatically retrieved in future conversations.
- **Open-source Arabic model**: Qwen3-8B, running with 4-bit quantization so it fits comfortably on a free GPU.

---

## 🚀 Running the Project

### 1) On Kaggle (the server)
```
Settings → Internet → On
Settings → Accelerator → GPU T4 x2 (or P100)
```
```bash
pip install -q transformers accelerate bitsandbytes fastapi uvicorn pyngrok nest_asyncio
```
- Paste your ngrok auth token into `kaggle_generate_server.py` (get one for free at [dashboard.ngrok.com](https://dashboard.ngrok.com/get-started/your-authtoken))
- Run the file — it will print a URL like `https://xxxx.ngrok-free.app`

### 2) Locally (backend + UI)
```bash
# Create and activate the virtual environment
./setup_env.sh          # macOS/Linux
.\setup_env.ps1         # Windows PowerShell

# Launch the interface
streamlit run streamlit_app.py
```
- Paste the Kaggle ngrok URL into the sidebar
- Click "Test Connection" to confirm the server is reachable
- Start chatting 🎉

---

## 🧰 Available Tools

| Tool | Purpose |
|---|---|
| `get_service_price` | Price of a given service (with or without a specific duration) |
| `get_trainers_for_specialty` | Trainers who specialize in a given discipline |
| `check_availability` | Real available time slots for a trainer on a given date |
| `book_appointment` | Executes the booking (automatically rejects already-booked slots) |
| `get_group_classes` | Group class schedule for a given weekday |
| `get_packages` | Available membership packages and their details |
| `retrieve_memory` | Retrieves previously saved customer preferences |
| `save_memory` | Saves a new preference worth remembering for future conversations |

---

## ⚠️ Important Notes

- **Demo data**: All prices, schedules, and data are fictional and for educational/demo purposes only — not real gym pricing.
- **The ngrok URL changes** every time the Kaggle server is restarted — remember to update it in the Streamlit sidebar each time.
- **Security**: Do not leave your ngrok auth token hardcoded in the code if you plan to publish this publicly (e.g. GitHub) — use an environment variable instead.
- **Open-source model caveat**: unlike closed APIs, there's no built-in structured tool-calling — parsing is done manually via regex on `<tool_call>` tags, so occasional parsing errors can occur.

---

## 🗺️ Roadmap

- [ ] Add a multi-agent layer (a Supervisor routing between a Booking Agent and a Complaints Agent)
- [ ] Evaluation suite to measure tool-calling accuracy against fixed test cases
- [ ] More stable deployment (instead of relying on ephemeral Kaggle sessions)
- [ ] Prompt-injection hardening for customer input

---

*An educational project for understanding how to build AI agents from scratch — from a hand-rolled ReAct loop to LangGraph, and wiring an open-source model through a distributed architecture.*
