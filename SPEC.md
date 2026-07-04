# PRD — Wanderlore: GenAI Travel & Culture Companion

> **Event:** PromptWar (Google × Hack2skill) — **Final Challenge**
> **One-liner:** Wanderlore helps travelers discover destinations and engage with local culture in meaningful ways — using Generative AI to recommend attractions, uncover hidden gems, tell immersive heritage stories (even from a photo you snap), surface real local events, and connect visitors with authentic cultural experiences.
> **Stack (locked):** Python + FastAPI on **Cloud Run** · **Gemini 3.5 Flash** via `google-genai` (structured output + **Google Search grounding** + **multimodal**) · **Firebase Auth** (Email/Password **and** Continue with Google) · **Cloud Firestore** (profiles, saved trips) · **Secret Manager** (Gemini key).
> **Evaluation criteria (design targets):** code quality, problem-statement alignment, security, testing, Google Cloud alignment.

---

## 1. Problem Statement

Travelers increasingly want *meaningful* trips — real culture, heritage, and local life — but the tools they use funnel everyone to the same crowded, top-10 tourist spots. Discovering hidden gems, understanding the story and heritage behind a place, finding what's *actually happening* during their visit, and connecting with authentic local experiences takes hours of scattered research across blogs, reviews, and forums. Wanderlore collapses that into one GenAI companion: describe your trip, and get personalized attractions, off-the-beaten-path gems, immersive heritage storytelling, current local events, and authentic cultural experiences — assembled into a day-by-day itinerary.

---

## 2. Goals

1. **Ship a live, judge-testable Cloud Run demo** where a signed-in user turns a destination + interests into a rich, personalized cultural discovery + itinerary.
2. **Cover all six required GenAI capabilities** as first-class, visible features (see §5 mapping).
3. **Ground factual output** (attractions, events) with **Google Search grounding** so recommendations are real and current, with citations — not hallucinated.
4. **Showcase multimodal Gemini**: point your camera at a landmark → identify it → get its heritage story.
5. **Keep a deterministic, unit-tested core** (itinerary day-packing) separate from the LLM.
6. **Score across all five criteria by design** (§13), building on the warmup that scored 96.6 / rank 3.

---

## 3. Non-Goals (out of scope for v1)

- **Booking / payments / ticketing** — we recommend and narrate; we don't transact. (Separate, heavy, regulated.)
- **Real-time maps / turn-by-turn navigation** — we suggest sequence and areas, not live routing. (Maps SDK integration is a fast-follow.)
- **Flights & hotels aggregation** — not what makes this culturally meaningful; commoditized elsewhere.
- **Full offline mode** — requires sync infra; premature for a demo.
- **User-generated content / social feed** — moderation + community are a separate initiative.
- **Guaranteed factual completeness** — grounded + cited, but a travel companion, not an official tourism authority.

---

## 4. User Stories

**Explorer (leisure traveler)**
- As a traveler, I want to enter a destination and my interests and get recommended attractions **with a reason each fits me**, so I don't sift through generic lists.
- As a traveler, I want **hidden gems** locals love, so my trip feels authentic, not touristy.
- As a traveler, I want an **immersive story** about a place — its history, legends, and heritage — so I feel connected, not just present.
- As a traveler, I want to **snap a photo of a landmark** and instantly learn what it is and its story, so I can explore spontaneously.

**Culture seeker**
- As a culture seeker, I want **authentic local experiences** (food, crafts, rituals, community) plus etiquette and useful phrases, so I engage respectfully.
- As a culture seeker, I want **real local events** happening on my dates (festivals, markets, performances), so I catch living culture, not just monuments.

**Planner**
- As a planner, I want my picks assembled into a **realistic day-by-day itinerary** that respects how many hours I want to spend each day, so I have a usable plan.
- As a returning user, I want to **sign in (with Google or email) and save trips**, so I can revisit and refine them.

**Edge / negative**
- Empty/absurd destination → validation error, not a broken plan.
- Landmark photo that isn't a landmark → app says "couldn't identify a landmark," not a fabricated story.
- Selecting more experiences than fit the days → itinerary packs what fits and clearly lists the **overflow** rather than silently dropping items.
- Unauthenticated request to a protected endpoint → `401`.

---

## 5. The six required GenAI capabilities → concrete features (alignment map)

| # | Required capability | Wanderlore feature | Gemini technique |
|---|---|---|---|
| 1 | **Recommend attractions** | Discover → ranked attractions with a personalized "why it fits you" | Structured output + **Search grounding** (real places) |
| 2 | **Uncover hidden gems** | Discover → "Beyond the guidebook" off-the-beaten-path list | Structured output + grounding |
| 3 | **Immersive storytelling** | Story mode → evocative narrative of a place's history & legends | Long-form generation; **multimodal** (photo → story) |
| 4 | **Promote heritage** | Heritage panel → cultural significance, traditions, preservation notes | Grounded generation + citations |
| 5 | **Suggest local events** | Events → festivals/markets/performances on the user's **actual dates** | **Google Search grounding** (current + cited) |
| 6 | **Connect w/ authentic cultural experiences** | Experiences → food, crafts, rituals, community + etiquette & phrases | Structured output |

The outputs assemble into a **personalized day-by-day itinerary** (deterministic packer), the tangible artifact the traveler leaves with.

---

## 6. Core flow

```
[0] AUTH            Firebase ID token (Email/Password OR Continue with Google) verified server-side
        │
[1] DISCOVER (Gemini + Search grounding)
        │   destination + dates + interests + pace →
        │   structured JSON: attractions[], hidden_gems[], experiences[], events[] (+ citations)
        │
[2] STORY (Gemini, text or multimodal)
        │   pick a place OR upload a landmark photo → identify + immersive heritage story
        │
[3] SELECT          user stars the attractions/gems/experiences they want
        │
[4] ITINERARY (pure Python — deterministic packer)
        │   selected items (each with a duration) + trip days + daily-hours budget →
        │   day-by-day schedule; overflow surfaced explicitly (NOT the LLM's job)
        │
[5] PERSIST         trip + itinerary + profile saved to Firestore
```

**Key design decision (tell the judges):** the LLM does discovery, storytelling, and cultural knowledge; **deterministic Python packs the itinerary** (fitting durations into day budgets). The scheduling logic is correct, explainable, and unit-tested — the LLM never silently drops a user's picks.

### Deterministic itinerary packer (pure function)
```python
def pack_itinerary(items, num_days, daily_minutes) -> Itinerary:
    # Greedy first-fit across days; anything that doesn't fit → overflow (surfaced, not dropped).
    days = [[] for _ in range(num_days)]
    used = [0] * num_days
    overflow = []
    for item in sorted(items, key=lambda i: i.duration_minutes, reverse=True):
        placed = False
        for d in range(num_days):
            if used[d] + item.duration_minutes <= daily_minutes:
                days[d].append(item); used[d] += item.duration_minutes; placed = True
                break
        if not placed:
            overflow.append(item)
    return Itinerary(days=days, minutes_used=used, overflow=overflow)
```

---

## 7. Data model & API

**Firestore layout**
```
users/{uid}                      → profile (name, email, photo, interests[], travel_style, home_city)
users/{uid}/trips/{tripId}       → saved { destination, dates, discover result, itinerary, createdAt }
```

**Gemini structured-output models** (also API response shapes): `Attraction`, `HiddenGem`, `CulturalExperience`, `LocalEvent`, `HeritageStory`, `LandmarkIdentification`, `DiscoverResult`, `Citation`.
**App-computed**: `ItineraryItem`, `ItineraryDay`, `Itinerary`, `UserProfile`.

**API** (all `/api/*` except health/config require a valid Firebase ID token)
| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/healthz` | public | health/readiness + smoke test (**not** bare `/healthz` — Google's frontend reserves it) |
| GET | `/api/config` | public | Firebase **web** config for the browser (non-secret) |
| GET/PUT | `/api/me` | ✅ | read / update profile & interests |
| POST | `/api/discover` | ✅ | attractions + hidden gems + experiences + events (grounded) |
| POST | `/api/story` | ✅ | immersive heritage story for a named place |
| POST | `/api/story/photo` | ✅ | **multimodal**: landmark photo → identify + story |
| POST | `/api/itinerary` | ✅ | deterministic day-packing of selected items |
| GET/POST | `/api/trips` | ✅ | list / save trips |

---

## 8. Requirements

### Must-Have — P0
| # | Requirement | Acceptance criteria |
|---|---|---|
| P0-1 | Auth: email/password **and** Google | Both sign-in methods work; protected APIs reject requests without a valid token (`401`). |
| P0-2 | Profile | After login the app shows name/email/photo and saved interests from Firestore. |
| P0-3 | Discover (attractions + hidden gems) | Valid request → ≥3 attractions (each with a personalized rationale) and ≥3 hidden gems. |
| P0-4 | Local events (grounded) | Events reflect the user's dates/destination and include **source citations** from Search grounding. |
| P0-5 | Cultural experiences | ≥3 authentic experiences plus etiquette tips / useful phrases. |
| P0-6 | Immersive storytelling | A place → a multi-paragraph heritage story (history, legend, significance). |
| P0-7 | Multimodal landmark story | A landmark photo → identification + story; a non-landmark → graceful "not identified". |
| P0-8 | Itinerary (deterministic) | Selected items packed into days within the daily-minutes budget; overflow surfaced, never silently dropped. |
| P0-9 | Structured Gemini output | Discovery/experiences use `response_schema`; malformed output is handled, never 500s. |
| P0-10 | Deployed on Cloud Run | Public URL; `GET /api/healthz` → 200. |
| P0-11 | Security baseline | No secrets in repo; token verified server-side; least-privilege SA; input + upload validation; prompt-injection handling. |

### Should-Have — P1
- Save/label multiple trips · regenerate a single section · "surprise me" destination · share a read-only itinerary link · profile interest editing.

### Could-Have — P2
- Google Maps embed & routing · audio narration (TTS) of stories · multi-language UI/output · offline export (PDF) · collaborative trips.

---

## 9. Google Cloud architecture

```
Browser ──HTTPS──▶ Cloud Run (FastAPI + static frontend)
  │ Firebase Auth JS (Email/Password + Google popup) → ID token
  │ every /api call: Authorization: Bearer <ID token>
  ▼
Cloud Run backend ──verify token──▶ Firebase Admin SDK (Auth)
  │ ADC (runtime SA)                ├── Cloud Firestore (profiles, trips)
  ▼                                 └── Gemini 3.5 Flash (google-genai)
Gemini: response_schema (structured) · Google Search grounding (events/attractions) · multimodal (landmark photo)
Secrets: Gemini API key in Secret Manager (mounted as env at deploy — never in repo)
Deploy: gcloud run deploy --source .  → Cloud Build → Artifact Registry
```

- **Model:** `gemini-3.5-flash` (fast, multimodal, supports grounding + structured output). Fallback `gemini-2.5-flash`. ⚠️ Confirm the current model ID at build time.
- **Grounding note:** Search grounding and a strict `response_schema` can conflict on one call; discovery does a **grounded pass** then a **structuring pass** (or returns grounded JSON + citations) — see engineering note in README.

---

## 10. Testing strategy (`pytest`) — targets testing + code-quality criteria

- **`test_itinerary.py`** (pure, no mocks — the crown jewel): items fit → packed correctly; over-capacity → correct `overflow`; empty items; zero days guard; minutes-used never exceeds budget.
- **`test_schemas.py`**: valid requests parse; bad input rejected; models round-trip.
- **`test_discover.py`** (fake Gemini): discovery returns attractions/gems/experiences/events; citations preserved; restricted/empty handled.
- **`test_story.py`** (fake Gemini): text story returns prose; photo path attaches the image part; non-landmark → `identified=false`.
- **`test_security.py`**: missing/invalid token → 401; dev bypass → demo user; valid token → identity.
- **`test_api.py`** (TestClient + dependency overrides): `/api/healthz` 200; `/api/discover` returns all sections; `/api/itinerary` packs; protected route → 401.
- All cloud clients are dependency-injected, so the suite runs with **no cloud credentials**.

---

## 11. Security

- **No secrets in code/repo/client.** Gemini key in **Secret Manager**, injected at deploy. Firebase **web** config is non-secret by design.
- **Auth server-side:** every protected route verifies the Firebase **ID token** (Admin SDK); Google & email/password both yield the same verified token. No trust in client claims.
- **Least privilege:** runtime SA limited to `roles/datastore.user` + `roles/secretmanager.secretAccessor` (on the secret).
- **Firestore rules:** user can read/write only `users/{uid}` where `uid == request.auth.uid`.
- **Input validation:** Pydantic types + size caps (destination, interests length, story prompt) + **image MIME/size limits** on the photo endpoint.
- **Prompt-injection mitigation:** user free text (destination notes, place names, photo captions) is inserted as clearly delimited **untrusted data**; system instructions forbid treating it as commands; `response_schema` constrains shape.
- **Grounding = anti-hallucination:** events/attractions cite real sources, reducing fabricated recommendations.
- **Transport/CORS:** HTTPS by default; CORS locked to the app origin. `.env` and service-account keys git-ignored.

---

## 12. Lessons applied from the warmup (don't repeat mistakes)

| Warmup issue | Fix baked in here |
|---|---|
| Bare `/healthz` was intercepted by Google's frontend | Health endpoint is **`/api/healthz`** from the start |
| Firebase Auth wasn't initialized (`CONFIGURATION_NOT_FOUND`) | **Setup checklist enables Email/Password + Google providers first**; README documents the one console step; app degrades gracefully |
| Billing not linked to the project | Reuse `promptwar-501405` (billing already linked) or link before deploy — documented in README |
| Gemini key pasted in chat | Key only in **Secret Manager**; README notes rotating it post-event |
| Model ID uncertainty | Pin `gemini-3.5-flash`, verified against the live API; documented fallback |

---

## 13. How this maps to the five judging criteria

| Criterion | How we win it |
|---|---|
| **Problem-statement alignment** | All six required capabilities are explicit P0 features (§5); output is a usable cultural itinerary; multimodal landmark storytelling is a memorable, on-theme demo. |
| **Code quality** | Layered, dependency-injected modules; typed Pydantic models; **LLM vs. deterministic** split (itinerary packer); lazy cloud imports for testability. |
| **Security** | Firebase Auth (Google + email, no passwords stored), server-side token verification, least-privilege SA, Firestore rules, Secret Manager, input + upload validation, prompt-injection handling. |
| **Testing** | `pytest`: pure itinerary tests + mocked-LLM discover/story + auth + API smoke; zero cloud creds needed. |
| **Google Cloud alignment** | Cloud Run + Gemini + Google **Search grounding** + Firebase Auth + Firestore + Secret Manager; one-command source deploy; IAM least privilege. |

---

## 14. Success metrics (demo-day)

- Discover returns all four sections in < ~10 s; events include ≥1 citation; landmark photo identified correctly in the demo; itinerary packs selected items with correct overflow; all tests green.
- Every discovery response contains attractions + hidden gems + experiences + events; every trip yields a usable day-by-day itinerary.

---

## 15. Open questions (genuinely open)

- **Region:** `GOOGLE_CLOUD_LOCATION` / Cloud Run region — reuse `asia-south1` (India-local) as warmup? *(you)*
- **Grounding vs. schema:** confirm whether one grounded call can also return strict JSON, or keep the two-pass approach. *(eng)*
- **Trip length input:** explicit dates vs. "N days"? Dates unlock real event grounding; "N days" is simpler. Default: **dates**. *(you)*
- **Output language:** English only for v1, or match the traveler's language? *(you)*
- **New Firebase web app vs. reuse warmup config:** reuse `promptwar-501405` web app or register a new one for Wanderlore? *(you / eng)*
