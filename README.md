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
- My Reports page uses server-side Telegram-linked ownership.
- Lifecycle management from UI (`active`, `resolved`, `deleted`) for owned reports.
- Optional photo upload with preview on report creation.
- Photo thumbnails on cards and larger media view on details/matches.
- Admin moderation page at `/admin` (Telegram-linked role checks).
- Responsive layout for phone/laptop.

### Backend API
- `POST /api/items`
- `GET /api/items/me` (requires Telegram-linked web session cookie)
- `GET /api/items`
- `GET /api/items/{id}`
- `PATCH /api/items/{id}`
- `DELETE /api/items/{id}`
- `GET /api/items/mine/{telegram_user_id}`
- `POST /api/items/{id}/resolve`
- `POST /api/items/{id}/reopen`
- `POST /api/items/{id}/delete` (soft delete)
- `POST /api/items/upload-image` (multipart image upload)
- `GET /api/items/search?q=...`
- `GET /api/items/search-smart?q=...&limit=...` (typo-tolerant ranked search with reasons)
- `GET /api/items/categories` (canonical category catalog)
- `GET /api/items/category-suggest?title=...` (category inference by title)
- `GET /api/items/matches/{id}`
- `GET /api/items/admin/items` (requires Telegram-linked admin/moderator session)
- `POST /api/items/admin/items/{id}/moderate` (approve/reject/flag/unflag)
- `POST /api/items/admin/items/{id}/verify`
- `POST /api/items/admin/items/{id}/lifecycle` (resolve/reopen/delete)
- `POST /api/items/{id}/flag` (public abuse report)
- `POST /api/items/claim-requests`
- `GET /api/items/claim-requests?telegram_user_id=...`
  - Optional `direction`: `all` (default), `incoming`, `outgoing`
- `POST /api/items/claim-requests/{id}/approve|reject|cancel|complete|not-match`
- OpenAPI docs at `/docs`.
- Auth/session endpoints:
  - `POST /api/auth/session`
  - `GET /api/auth/me`
- `POST /api/auth/link-code`
- `POST /api/auth/link/confirm` (used by bot `/link`)
- `POST /api/auth/logout`
- `POST /api/auth/unlink`

### Telegram assistant
- `/start`
- `/new` guided conversation
- `/list`
- `/search <query>`
- `/search <query>` now uses fuzzy/token smart ranking with readable match reasons.
- `/lost`
- `/found`
- `/myitems` for ownership-based report management.
- `/link <code>` to bind website session with Telegram account.
- `/flag <item_id> <reason>` to report abuse/spam.
- `/claims` to track claim/contact workflow.
- `/whoami` to display Telegram account id/username/name and admin role access.
- `/clear` resets FSM state, clears pending wizard data, removes stale keyboards, and attempts best-effort deletion of recent private-chat messages (with explicit success/failure counts).
- `/new` category step now supports a richer catalog with inline keyboard pagination and auto-suggested category after title entry.
- `/new` wizard includes a photo step (send photo or skip).
- After `/new`, bot displays matches and sends strong-match notifications to relevant Telegram owners.

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

## Item Lifecycle & Management

- Reports now have a lifecycle field:
  - `active` (default)
  - `resolved`
  - `deleted` (soft delete)
- Matching/search defaults to active reports.
- Resolved/deleted reports are excluded from normal match candidate pools.
- Ownership-sensitive actions (`resolve/reopen/delete`) are server-authorized using linked Telegram identity (web session) or bot Telegram id.
- Raw `DELETE /api/items/{id}` is admin-only (Telegram-linked role check) and should be treated as moderation-only.

## Moderation & Trust/Safety

- Reports have moderation status: `pending`, `approved`, `rejected`, `flagged`.
- Default moderation is `approved` for quick publishing.
- Public listing/search/matches only use `approved` reports.
- Rejected/flagged reports are removed from normal public matching flows.
- Reports can be marked as verified (`is_verified=true`) by admins to improve trust signals.

## Claim / Contact / Handoff Flow

- Users can create a claim from one matched item to another (`pending`).
- Target owner can approve/reject; requester can cancel; either participant can mark complete/not-match.
- Contact details are shared only after claim is `approved` or `completed`.
- Completing a claim resolves both linked items.
- Marking not-match prevents that pair from being surfaced again as a primary match candidate.

## Admin & Moderator Access (Telegram-linked, server-side)

- Admin authorization is based on linked Telegram identity from the web session cookie.
- Backend checks env-configured allowlists:
  - `ADMIN_TELEGRAM_USER_IDS` (primary trusted identifier)
  - `ADMIN_TELEGRAM_USERNAMES` (fallback convenience)
- Role mapping in this project:
  - `admin`: Telegram user ID matched
  - `moderator`: Telegram username matched (when ID did not match)
- `/admin` uses Telegram-linked session flow. No password-style admin login is required.
- Backend is the source of truth for access decisions.
- Optional fallback for development only: `ALLOW_ADMIN_SECRET_FALLBACK=true` with `X-Admin-Secret`.
- Web navigation shows **Moderation** entry and admin role chip only for authorized linked admin/moderator sessions.

### First-time bootstrap (username) ➜ migrate to user ID (recommended)

1. Put your Telegram username in `ADMIN_TELEGRAM_USERNAMES` for first-time bootstrap.
2. Start backend+web+bot and link your website session with `/link <code>`.
3. In Telegram bot, run `/whoami` and copy your numeric Telegram user id.
4. Move to secure ID-based config:
   - add your ID to `ADMIN_TELEGRAM_USER_IDS`
   - remove username from `ADMIN_TELEGRAM_USERNAMES` (or leave empty)
5. Restart services.

This keeps Telegram-linked auth as the source of truth while transitioning to the stronger immutable identifier.

### Configure in `.env`

```dotenv
ADMIN_TELEGRAM_USER_IDS=
ADMIN_TELEGRAM_USERNAMES=Leo0742
ALLOW_ADMIN_SECRET_FALLBACK=false
```

Tips:
- Use IDs wherever possible because usernames can change.
- Username matching is case-insensitive and supports optional `@`.

### How to find your Telegram user ID

- Use Telegram helper bot like `@userinfobot`, or
- Log incoming Telegram updates in your own bot and read `from.id`.

### Local admin access test

1. Copy env and edit admin variables:
   ```bash
   cp .env.example .env
   ```
2. For first login bootstrap, set:
   ```dotenv
   ADMIN_TELEGRAM_USER_IDS=
   ADMIN_TELEGRAM_USERNAMES=<your_telegram_username_without_@>
   ALLOW_ADMIN_SECRET_FALLBACK=false
   ```
3. Start stack:
   ```bash
   docker compose up --build
   ```
4. Open `/admin`.
5. If prompted, generate link code and send `/link <code>` to your bot.
6. In bot, run:
   ```text
   /whoami
   ```
   Confirm it shows `Admin access: yes` and note `Telegram user id`.
7. Update `.env` to switch to ID-based allowlist:
   ```dotenv
   ADMIN_TELEGRAM_USER_IDS=<your_numeric_telegram_user_id>
   ADMIN_TELEGRAM_USERNAMES=
   ALLOW_ADMIN_SECRET_FALLBACK=false
   ```
8. Restart backend and bot:
   ```bash
   docker compose up --build backend bot
   ```
9. Verify:
   - `/whoami` still shows admin access with role
   - `/admin` loads moderation UI
   - if removed from allowlists, `/admin` shows access denied and hides admin nav

## Anti-Spam Rules

- Rate limit on create: max `CREATE_RATE_LIMIT_MAX_ITEMS` within `CREATE_RATE_LIMIT_WINDOW_MINUTES`.
- Duplicate protection blocks repeated same title/description/contact within 24 hours.

## Bot Search & Category UX Upgrade

- Smart search (`/search`) is now typo-tolerant and punctuation/case-insensitive.
- Ranking combines fuzzy title match, partial text match, token overlap, and location/category similarity.
- `/new` flow category step now includes:
  - large practical category catalog
  - inline keyboard browsing (paged)
  - auto-suggested category inferred from title (user can accept/change)
- `/clear` now reports how much cleanup was actually performed, instead of claiming full chat wipe when Telegram limits prevent it.
- Very low-quality/gibberish-like text submissions are rejected.

## Media Storage (Local, Persistent)

- Uploaded photos are stored locally in backend media directory: `/app/media`.
- Backend serves files via `/media/<image_path>`.
- Docker compose mounts a persistent named volume for media (`media_data`) so files survive container restarts.
- Supported image types: JPEG / PNG / WEBP.
- Max upload size is controlled by backend setting `MEDIA_MAX_BYTES` (default: 5MB).

## Bot: My Items & Management

- Use `/myitems` (or **My Items** keyboard button) to list and manage your reports.
- Each item card includes actions:
  - Show Matches
  - Mark Resolved / Reopen
  - Delete (soft)
- Bot verifies ownership via the same Telegram identity used by linked web sessions.
- When item photos exist, `/myitems` cards are sent as photo messages with captions.

## Bot: Photo Upload Flow

- In `/new`, the wizard now includes a **Photo** step.
- User can:
  - send a photo
  - tap **Skip Photo**
- Back/Cancel behavior still works across wizard steps.
- Review screen shows whether a photo is attached.

## Website Ownership: Telegram Linked (server-side source of truth)

- localStorage is **not** used as ownership source of truth anymore.
- Website creates/uses an HTTP-only session cookie (`lfb_session`) on backend.
- User clicks **Connect Telegram** in web UI, gets short link code, and sends `/link <code>` to the Telegram bot.
- Bot confirms link via `POST /api/auth/link/confirm`; backend stores Telegram identity in the session.
- `My Reports` now loads from `GET /api/items/me` and ownership checks are performed server-side.
- Reports created from website are stored with owner identity fields (`owner_telegram_user_id`, `owner_telegram_username`, `owner_display_name`).
- The same owner identity is used in bot `/myitems`, claims, and lifecycle actions across devices.

## Automatic Match Notifications (Bot)

- After creating a new item in bot, if strong matches are found (score threshold), bot:
  - notifies the creator
  - notifies matched item owners when `telegram_user_id` is available
- Notification failures are swallowed and do not block item creation flow.
- If matched items include photos, notifications may include image media.
- Matches are moderation-aware: rejected/flagged items are excluded from match candidates.

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
