<<<<<<< HEAD
# Social Media Engagement Agent backend
=======
# Influx.AI backend
>>>>>>> 684df2d (Synchornized data)

FastAPI is a thin application API. It does not generate answers or retain chat
history itself:

<<<<<<< HEAD
## Remaining manual step: OpenClaw + Hindsight 
=======
    React -> FastAPI -> OpenClaw Gateway -> Groq gpt-oss-120b
                                      -> Hindsight Cloud auto-recall/retain
>>>>>>> 684df2d (Synchornized data)

## Configure

Copy `.env.example` to `.env` and set the OpenClaw Gateway token plus the
Hindsight Cloud token. Never commit either secret.

OpenClaw must have:

- the official `hindsight-openclaw` plugin enabled and pointed at Hindsight Cloud;
- Groq `gpt-oss-120b` configured as its default agent model;
- `gateway.http.endpoints.chatCompletions.enabled: true`.

## Run

    source venv/bin/activate
    pip install -r requirements.txt
    uvicorn main:app --reload

## API

- `POST /chat`: forwards exactly one user turn to
  `/v1/chat/completions` using `model: openclaw/default`. Hindsight performs
  recall and retention through the OpenClaw plugin.
- `GET /memory`: returns live memory counts, a Hindsight-synthesized creator
  profile, and latest memory.
- `POST /analytics`: retains a real performance entry in Hindsight Cloud.
- `GET /analytics`: returns Hindsight-backed entries and computed averages,
  best format, and comparison insight.
