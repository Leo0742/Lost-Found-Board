# Lost & Found Board

**One sentence:** Lost & Found Board is a web application with a Telegram assistant for posting and searching lost or found items.

## MVP Architecture

- **Backend API:** FastAPI + SQLAlchemy + Alembic.
- **Database:** PostgreSQL.
- **Frontend:** React + Vite + TypeScript served by Caddy.
- **Telegram assistant:** aiogram bot that talks to backend REST API.
- **Deployment:** Docker Compose for VM/local setup.

The codebase is intentionally modular for hackathon speed:
- `routers` / `schemas` / `services` / `models` split in backend.
- Telegram bot uses API client (no direct DB access).
- Rule-based matching logic isolated in one service.

## Folder Structure

```text
.
├── backend/
│   ├── alembic/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── scripts/
│   └── tests/
├── bot/
├── frontend/
└── docker-compose.yml
```

## Features

### Web app
- Item list page with card UI.
- Filters: status (`lost`/`found`/all), keyword query, optional category.
- Create item page.
- Item detail page.
- Responsive layout for phone/laptop.

### Backend API
- `POST /api/items`
- `GET /api/items`
- `GET /api/items/{id}`
- `PATCH /api/items/{id}`
- `DELETE /api/items/{id}`
- `GET /api/items/search?q=...`
- `GET /api/items/matches/{id}`
- OpenAPI docs at `/docs`.

### Telegram assistant
- `/start`
- `/new` guided conversation
- `/list`
- `/search <query>`
- `/lost`
- `/found`
- After `/new`, bot displays possible matches from backend.

### Matching logic (hybrid local, no external API)
- Opposite status hard filter (`lost` vs `found`).
- Text normalization (case/punctuation cleanup, alias/synonym mapping, simple RU->EN transliteration, location alias normalization).
- Rule-based signals (category compatibility, keyword overlap, location overlap).
- Fuzzy matching with RapidFuzz for title/location/object-type robustness to typos.
- Local semantic similarity using FastEmbed (CPU model, no cloud inference).
- Lightweight reranking/boosting based on semantic + extracted feature alignment.
- Match output includes score, confidence (`high`/`medium`/`low`), and human-readable reasons.

## Quick Start (Docker Compose)

1. Reset containers and DB volume (recommended after failed migration attempts):
   ```bash
   docker compose down -v
   ```
2. Copy env values:
   ```bash
   cp .env.example .env
   ```
3. (Optional for web/api only) keep `TELEGRAM_BOT_TOKEN=replace_me`.
4. Start core stack (db + backend + frontend):
   ```bash
   docker compose up --build
   ```
5. Open:
   - Web UI: `http://localhost`
   - Backend docs: `http://localhost/api/docs` (proxied)

### Start Telegram bot (optional)

1. Set a real token in `.env`:
   ```dotenv
   TELEGRAM_BOT_TOKEN=<your-real-token>
   ```
2. Start with bot profile enabled:
   ```bash
   docker compose --profile bot up --build
   ```

If the bot profile is enabled without a valid token, the bot container exits immediately with a clear `TELEGRAM_BOT_TOKEN is required` message.


## Local Semantic Model Notes

- Backend uses FastEmbed with `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` by default.
- Model runs locally on CPU and model files are cached on first use.
- No external inference API calls are used (local inference only).
- You can override model via env: `EMBEDDING_MODEL_NAME=<model-name>`.

## Local Development (without Docker)

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Bot
```bash
cd bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Seed Demo Data

```bash
cd backend
python scripts/seed.py
```

## Testing

```bash
cd backend
pytest
```

## VM Deployment Notes

- Install Docker + Docker Compose plugin on VM.
- Clone repository and configure `.env`.
- Run `docker compose up -d --build`.
- Put VM domain/IP in front of Caddy port 80.
- For HTTPS, update `frontend/Caddyfile` to use your domain and TLS email.


## Exact Run Instructions (Docker)

```bash
cp .env.example .env
docker compose down -v
docker compose up --build
```

Then open:
- `http://localhost` (frontend)
- `http://localhost/api/docs` (backend docs)

## Verification Checklist

1. Create a `lost` item: `black wallet with student card` in `dormitory A entrance`.
2. Create a `found` item: `dark card holder found near dorm A`.
3. Open item details or call `GET /api/items/matches/{id}`.
4. Confirm a match appears with:
   - score (0-10),
   - confidence label,
   - reasons like `matching object type`, `similar location`, `semantic similarity detected`.
5. Try typo case (`airpods csae` vs `apple earbuds case`) and confirm it still matches.

## Demo Scenario

Input pair:
- Lost: `black wallet with student card`, location `dormitory A entrance`
- Found: `dark card holder found near dorm`, location `near dorm A`

Expected behavior:
- `dark -> black` and `card holder -> wallet` normalization aligns terms.
- Location aliases normalize to the same campus zone.
- Fuzzy matching tolerates wording differences.
- Embedding similarity catches contextual equivalence.
- Match is returned with medium/high confidence and explanation reasons.
