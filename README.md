# Lost & Found Board

## One-line description
A web app + Telegram bot for posting, discovering, and managing lost-and-found item reports.

## Demo

Screenshots are expected for final submission/repository polish and must be added manually by the repository owner.

Place screenshots in: `docs/screenshots/`

Use these exact filenames and contents:
- `docs/screenshots/home.png` — main Items/board page of the web app, showing the homepage or item listing interface in a clean state.
- `docs/screenshots/new-report.png` — Create Report / New Report page with the report creation form visible in a clean state.

The README already points to the correct location and expected content. Add screenshots to `docs/screenshots/` before final submission.

## Product context

**End users**
- Students, campus staff, office teams, event organizers, or any community that needs a shared lost-and-found board.

**Problem**
- Lost/found information is usually fragmented across chats and personal messages, making matching and owner handoff slow.

**Solution**
- Lost & Found Board centralizes reports in a searchable web app and Telegram bot, with matching, moderation, claim workflow, and Telegram-linked identity for trusted ownership actions.

## Features

### Implemented features

**Web app**
- Browse lost/found listings with filters and search.
- Create reports with status, category, location, details, contact info, and optional image upload.
- View item details and match suggestions.
- Manage own reports in **My Reports** (resolve/reopen/delete).
- Profile page with contact/address management.
- Telegram link flow for secure session ownership.
- Admin moderation page for authorized Telegram-linked admins/moderators.

**Backend API (FastAPI)**
- CRUD-style item/report endpoints with lifecycle states (`active`, `resolved`, `deleted`).
- Matching endpoints and smart search.
- Claim workflow endpoints (approve/reject/cancel/complete/not-match).
- Anti-abuse protections (rate limits, duplicate suppression, abuse events).
- Auth/session endpoints with CSRF-aware cookie sessions.
- Readiness/health endpoints.

**Telegram bot**
- Guided `/new` wizard (including optional photo step).
- Search and listing commands (`/search`, `/list`, `/lost`, `/found`).
- `/myitems` management actions and match viewing.
- Session linking via `/link <code>`.
- Claim and abuse report commands (`/claims`, `/flag`).

### Not yet implemented / planned features
- No dedicated iOS/Android native app (web + Telegram only).
- No cloud object storage integration; media is stored on local backend volume.
- No external OAuth providers; identity is based on Telegram session linking.

## Usage

### Web app usage
1. Open the web app.
2. Browse reports on the home page and filter/search by keyword, status, and category.
3. Open **Report Item** to submit a new lost/found report (optionally with a photo).
4. Open an item card to view details and match suggestions.
5. Use **My Reports** to manage your own reports (resolve/reopen/delete).
6. Use **Profile** to maintain contact/address data used in flows like claims.

### Telegram bot usage
1. Start bot with `/start`.
2. Create report with `/new` (step-by-step wizard).
3. Search with `/search <query>` or browse `/lost`, `/found`, `/list`.
4. Manage personal reports via `/myitems`.
5. Link web session via `/link <code>` when prompted from the website.
6. Use `/claims` to track item handoff claims.

## Deployment

### Target VM OS
- **Ubuntu 24.04 LTS**

### Prerequisites on VM
Install:
- Git
- Docker Engine
- Docker Compose plugin (`docker compose`)

Example install (Ubuntu 24.04):
```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg git
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```
Log out and back in once after adding your user to the `docker` group.

### 1) Clone project
```bash
git clone https://github.com/Leo0742/Lost-Found-Board.git
cd Lost-Found-Board
```

### 2) Configure `.env`
```bash
cp .env.example .env
```
Edit `.env` for production:
- Set strong `POSTGRES_PASSWORD`.
- Set non-default `INTERNAL_API_TOKEN`.
- Keep `STRICT_INTERNAL_TOKEN=true`.
- Set `APP_ENV=prod`.
- Set admin allowlist (`ADMIN_TELEGRAM_USER_IDS`, optionally usernames for bootstrap).
- Set `TELEGRAM_BOT_TOKEN` only if bot will be enabled.
- Optionally set `WEB_PORT` if you do not want port `80`.

### 3) Start services (Docker Compose)
Start web + backend + db:
```bash
docker compose up -d --build db backend web
```

Optional: start Telegram bot profile:
```bash
docker compose --profile bot up -d --build bot
```

### 4) Verify deployment
Check containers:
```bash
docker compose ps
```

Check backend readiness:
```bash
curl -f http://localhost/api/ready
```

Open in browser:
- Web UI: `http://<VM_IP>:${WEB_PORT:-80}`
- API docs: `http://<VM_IP>:${WEB_PORT:-80}/api/docs`

### 5) Basic operational check
- Create one `lost` and one `found` report from web or bot.
- Open item details and confirm matches are returned.
- If using bot, test `/start`, `/new`, and `/search`.

### Optional local development workflow
If needed, a non-Docker local path exists for backend/frontend/bot using Python virtualenv + npm scripts.
