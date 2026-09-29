# Influx.AI — Social Media Engagement Agent

> **An AI-powered social media strategist that remembers your creator journey, learns from engagement patterns, and gives personalized content recommendations across conversations.**

## The Problem

Most AI content assistants forget everything after each chat, forcing creators to repeatedly explain their niche, audience, and goals. Even built-in social media analytics only show historical metrics—they don't remember what your audience consistently responds to or use that knowledge in future conversations.

## Our Solution

**Influx.AI** combines conversational AI with persistent creator memory.

Instead of starting from scratch every time, it remembers your creator profile, audience preferences, top-performing formats, and recurring community requests to deliver personalized recommendations that improve over time.

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

## Example

**First conversation**

> "I'm a beginner fitness creator."

Influx.AI remembers:

* Niche: Beginner Fitness
* Goal: Increase saves and shares
* Audience: Women 18–30
* Best posting time: 8 PM carousels, 7 AM reels

**New conversation**

> "What should my next post be?"

Instead of asking for the niche again, it recommends a fitness-specific post using previously learned audience insights.

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
* Llama models

### Storage

* SQLite / Persistent backend memory
* JSON-based memory layer

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
