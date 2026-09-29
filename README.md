# Influx.AI — Social Media Engagement Agent

> **An AI-powered social media strategist that remembers your creator journey, learns from engagement patterns, and gives personalized content recommendations across conversations.**

## The Problem

Content creators often don't know what to post next. Existing analytics only show past performance and don't analyze audience behavior, identify recurring content preferences, or recommend the next best piece of content based on what has consistently worked. As a result, creators are left interpreting numbers instead of receiving actionable content strategy.

## Our Solution

Influx.AI goes beyond analytics. It learns from a creator's content history, remembers audience preferences across conversations, and recommends the next best post—along with the best format, timing, and strategy—to help creators make smarter content decisions over time.

## Key Features

* **Persistent Creator Memory** – Remembers niche, audience, goals, and preferences across conversations.
* **AI Content Recommendations** – Suggests personalized post ideas based on long-term context.
* **Audience Memory** – Tracks recurring audience requests and interests.
* **Performance Insights** – Learns which formats and posting times perform best.
* **Memory Dashboard** – Displays stored creator memories and learned insights.
* **Natural Onboarding** – If important creator details are missing, the AI asks for them and saves them automatically.

## How It Works

1. The creator shares their niche, goals, and audience.
2. Influx.AI stores these as long-term creator memories.
3. Each conversation updates learned insights from new interactions.
4. Future chats automatically load this context before generating recommendations.


## Tech Stack

### Frontend

* React
* Vite
* Tailwind CSS

### Backend

* FastAPI
* Python
* Uvicorn

### AI

* Groq API
* OpenClaw – AI agent framework

### Storage

* SQLite
* Hindsight Cloud

## Project Structure

```text
social-memory-agent/
│── frontend/
│── backend/
│── README.md
```

## Installation

### Clone

```bash
git clone https://github.com/Thanishka15/SocioM-Agent-.git
cd SocioM-Agent-
```

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

```bash
cd ../frontend
npm install
npm run dev
```

## Future Roadmap

* Instagram account integration
* Real engagement analytics
* Audience segmentation
* Automated content calendar
* Trend-aware recommendations
* Multi-platform support (Instagram, LinkedIn, X)

## What Makes It Different?

Unlike generic AI assistants, Influx.AI builds a **long-term memory** for every creator. It doesn't just analyze yesterday's engagement—it remembers what consistently works for your audience and uses that knowledge to improve future recommendations.

## Team

Built for **Hyderabad 3.0 Hackathon**.
