# Social Memory Agent backend

This service has no database and no local-memory fallback. OpenClaw runs every chat turn and its official Hindsight plugin owns recall and retention.

## Remaining manual step: OpenClaw + Hindsight CLI

Install the official plugin, then use its wizard. Select Embedded daemon and Groq when prompted.

    openclaw plugins install @vectorize-io/hindsight-openclaw
    npx --package @vectorize-io/hindsight-openclaw hindsight-openclaw-setup

Enable the OpenClaw Chat Completions endpoint, keep a stable bank for this creator app, then start the gateway:

    openclaw config set gateway.http.endpoints.chatCompletions.enabled true
    openclaw config set plugins.entries.hindsight-openclaw.config.dynamicBankId false
    openclaw config set plugins.entries.hindsight-openclaw.config.bankId social-media-agent
    openclaw gateway

Copy any non-default Hindsight endpoint, bank, or token values to .env.

## Run

    cd backend
    source venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    uvicorn main:app --reload

## Endpoints

- POST /chat forwards an agent turn to OpenClaw. The plugin auto-recalls before it and auto-retains after it.
- GET /memory lists units from the configured Hindsight bank.
- POST /analytics retains a manual engagement event in Hindsight.
- GET /analytics lists Hindsight items created through the analytics endpoint.

If either dependency is unavailable, the API returns HTTP 503 intentionally. No app-owned memory exists.

