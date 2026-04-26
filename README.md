# Podium — AI Public Speaking Coach

> Built for LA Hacks 2026 · Fetch.ai Agentverse Prize Track

Podium is a real-time AI public speaking coach that puts you in front of a live, reactive virtual audience. Speak, get instant feedback on your delivery, and ask follow-up questions powered by ASI:One — all in one session.

---

## What It Does

Most people practice speeches alone, with no feedback and no pressure. Podium changes that by simulating a real audience that reacts to how you speak — not just what you say.

- **Live audience simulation** — 8–20 AI avatars react emotionally in real time based on your delivery
- **Real-time coaching** — voice tips delivered mid-session targeting your specific weaknesses
- **Speech analysis** — filler words, pace (WPM), eye contact, and vocal energy tracked continuously
- **Argument analysis** — AI finds the weakest point in your argument and challenges you with a hard adversarial question
- **Session breakdown** — personalized post-session report with high/low moments, strengths, and next steps
- **ASI:One follow-up chat** — ask the Podium coach agent anything about your session, powered by the Fetch.ai Agentverse

---

## Architecture

Podium is built on a **multi-agent system** using the [Fetch.ai uAgents framework](https://fetch.ai/docs/guides/agents/getting-started/create-a-uagent):

| Agent | Role |
|---|---|
| `coach_agent` | Main Agentverse entrypoint — handles ASI:One chat and REST coaching queries |
| `speech_agent` | Transcribes audio via ElevenLabs STT, detects filler words and pace |
| `vision_agent` | Analyzes webcam frames for eye contact and facial engagement |
| `fusion_agent` | Combines speech + vision signals into a unified engagement score |
| `audience_agent` | Drives emotional reactions for each audience avatar |
| `argument_agent` | Identifies logical gaps and generates adversarial challenge questions |

The frontend connects via WebSocket to a FastAPI backend that orchestrates all agents in real time.

---

## Tech Stack

- **Frontend** — React + Vite + TypeScript
- **Backend** — FastAPI + WebSockets
- **Agents** — Fetch.ai uAgents + Agentverse mailbox
- **AI** — ASI:One (LLM), ElevenLabs (STT + TTS), Groq (llama-3.3-70b)
- **Database** — MongoDB (optional, app runs without it)

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ and pnpm
- ElevenLabs API key
- Groq API key
- ASI:One API key

### Backend Setup

```bash
# Clone the repo
git clone https://github.com/jss0218/SpeakBetter.git
cd SpeakBetter

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r podium/requirements.txt

# Configure environment
cp podium/.env.example podium/.env
# Fill in your API keys in podium/.env
```

### Running the App

```bash
# Terminal 1 — FastAPI backend (WebSocket + session handling)
PYTHONPATH=. uvicorn podium.main:app --port 8001 --reload

# Terminal 2 — Coach agent (Agentverse + ASI:One chat)
PYTHONPATH=. python podium/agents/coach_agent.py

# Terminal 3 — Frontend
cd frontend
pnpm install
pnpm dev
```

Open `http://localhost:5173` in your browser.

### Environment Variables

Create `podium/.env` with:

```env
ELEVENLABS_API_KEY=your_key_here
ELEVENLABS_STT_MODEL_ID=scribe_v2
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
ASI1_API_KEY=your_key_here
MONGODB_URI=mongodb://localhost:27017  # optional
```

---

## Agentverse Integration

The `coach_agent` is registered on [Agentverse](https://agentverse.ai) and discoverable via ASI:One. It exposes:

- **Chat Protocol** — compatible with `uagents_core.contrib.protocols.chat`, allowing ASI:One users to chat with the Podium coach directly
- **REST GET** `/rest/get` — agent status check
- **REST POST** `/rest/post` — submit a coaching question, get an AI response

Anyone on ASI:One can find **podium-coach-agent** and get public speaking advice without running the app.

---

## Team

Built at LA Hacks 2026 for the Fetch.ai Agentverse prize track.
