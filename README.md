# 🧭 Wanderlore — GenAI Travel & Culture Companion

Wanderlore helps travelers **discover destinations and engage with local culture in meaningful ways**. Tell it where you're going and it uses Generative AI to **recommend attractions**, **uncover hidden gems**, tell **immersive heritage stories** (even from a photo you snap), surface **real local events**, and connect you with **authentic cultural experiences** — then packs your picks into a day-by-day itinerary.

Built for **PromptWar (Google × Hack2skill) — Final Challenge**.

> Full product spec: [SPEC.md](SPEC.md)

---

## The six required GenAI capabilities → features

| Required capability | Feature | Gemini technique |
|---|---|---|
| Recommend attractions | Discover → attractions w/ "why it fits you" | structured output |
| Uncover hidden gems | Discover → off-the-beaten-path list | structured output |
| Immersive storytelling | Story drawer (text) + **photo → story** | long-form + **multimodal** |
| Promote heritage | Heritage note on every story | grounded generation |
| Suggest local events | Events on your dates, **with sources** | **Google Search grounding** |
| Connect w/ authentic experiences | Experiences + etiquette & phrases | structured output |

The picks assemble into a **deterministic, unit-tested itinerary** — the LLM suggests, plain Python packs.

---

## Architecture (Google Cloud)

```
Browser ──HTTPS──▶ Cloud Run (FastAPI + static frontend)
  │ Firebase Auth (Email/Password + Continue with Google) → ID token
  │ every /api call: Authorization: Bearer <ID token>
  ▼
Cloud Run backend ──verify token──▶ Firebase Admin SDK (Auth)
  │ ADC (runtime SA)                ├── Cloud Firestore (profiles, trips)
  ▼                                 └── Gemini 3.5 Flash (google-genai)
Gemini: response_schema · Google Search grounding (events) · multimodal (landmark photo)
Secrets: Gemini API key in Secret Manager (never in repo)
```

- **Model:** `gemini-3.5-flash` (fast, multimodal, grounding + structured output). Fallback `gemini-2.5-flash`.
- **LLM vs. deterministic split:** discovery/storytelling by Gemini; itinerary packing by `app/itinerary.py` (pure, tested).

---

## Project layout

```
app/
  main.py         FastAPI app, routers, static mount, /api/healthz
  config.py       env-driven settings
  schemas.py      Pydantic models (also Gemini response_schema)
  itinerary.py    deterministic day-packer (pure, unit-tested)
  gemini_client.py google-genai wrapper: structured · grounded · multimodal (lazy import)
  discover.py     attractions/gems/experiences (structured) + events (grounded)
  story.py        heritage story (text) + landmark photo → story (multimodal)
  security.py     Firebase ID token verification
  repository.py   Firestore data access
  deps.py         dependency-injection providers (overridable in tests)
  routes/         meta · profile · travel
frontend/         index.html (landing) · login.html · app.html · *.css · *.js
tests/            pytest suite (runs with NO cloud credentials)
Dockerfile · requirements*.txt · .env.example · SPEC.md
```

---

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env    # fill in GEMINI_API_KEY + FIREBASE_* (or set AUTH_REQUIRED=false for a quick look)
uvicorn app.main:app --reload --port 8080
# open http://localhost:8080
```

## Test

```bash
pytest
```

All external clients are dependency-injected fakes → the suite needs **no cloud credentials**.

---

## Deploy to Cloud Run (project `promptwar-501405`)

```bash
# APIs (billing already linked to this project)
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com firestore.googleapis.com secretmanager.googleapis.com \
  --project promptwar-501405

# Gemini key → Secret Manager (never in the repo)
printf '%s' "$GEMINI_API_KEY" | gcloud secrets create wanderlore-gemini-key --data-file=- --project promptwar-501405

# Deploy from source
gcloud run deploy wanderlore --source . --region asia-south1 --allow-unauthenticated --memory 1Gi \
  --set-env-vars "USE_VERTEXAI=false,AUTH_REQUIRED=true,GEMINI_MODEL=gemini-3.5-flash,FIREBASE_PROJECT_ID=promptwar-501405,FIREBASE_WEB_API_KEY=...,FIREBASE_AUTH_DOMAIN=promptwar-501405.firebaseapp.com,FIREBASE_APP_ID=..." \
  --set-secrets "GEMINI_API_KEY=wanderlore-gemini-key:latest"

# Least-privilege IAM for the runtime service account ($SA)
gcloud projects add-iam-policy-binding promptwar-501405 --member="serviceAccount:$SA" --role=roles/datastore.user --condition=None
gcloud secrets add-iam-policy-binding wanderlore-gemini-key --member="serviceAccount:$SA" --role=roles/secretmanager.secretAccessor --project promptwar-501405
```

### One-time Firebase Auth setup (required for login)
In the [Firebase Console → Authentication](https://console.firebase.google.com/project/promptwar-501405/authentication/providers) → **Get started**, enable **Email/Password** *and* **Google**. (Providers can't be enabled from scratch via API — this is the single console step.)

**Firestore rules** (defense in depth):
```
rules_version = '2';
service cloud.firestore {
  match /databases/{db}/documents {
    match /users/{uid}/{document=**} {
      allow read, write: if request.auth != null && request.auth.uid == uid;
    }
  }
}
```

---

## How this maps to the judging criteria

| Criterion | Where |
|---|---|
| **Problem alignment** | All six capabilities are P0 features; multimodal landmark storytelling + grounded events are memorable, on-theme. |
| **Code quality** | Layered, dependency-injected modules; typed models; LLM-vs-deterministic split; lazy cloud imports. |
| **Security** | Firebase Auth (Google + email, no passwords stored), server-side token verification, least-privilege SA, Firestore rules, Secret Manager, input + upload validation, prompt-injection handling, grounded (anti-hallucination) events. |
| **Testing** | `pytest`: pure itinerary tests + mocked-LLM discover/story + auth + API smoke; zero cloud creds. |
| **Google Cloud alignment** | Cloud Run + Gemini + Google Search grounding + Firebase Auth + Firestore + Secret Manager; one-command source deploy. |

## Lessons applied from the warmup
Health endpoint is **`/api/healthz`** (Google's frontend reserves bare `/healthz`) · Firebase Auth provider enablement documented upfront · billing already linked to `promptwar-501405` · Gemini key only in Secret Manager · model id verified against the live API.
