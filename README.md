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

### Matching logic (rule-based)
- Opposite status only (`lost` vs `found`).
- Same category boost.
- Keyword overlap in title/description.
- Similar location token overlap.
- Returns top scored results.

## Quick Start (Docker Compose)

1. Copy env values:
   ```bash
   cp .env.example .env
   ```
2. Add your real Telegram token in `.env` (`TELEGRAM_BOT_TOKEN`).
3. Run:
   ```bash
   docker compose up --build
   ```
4. Open:
   - Web UI: `http://localhost`
   - Backend docs: `http://localhost/api/docs` (proxied)

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
