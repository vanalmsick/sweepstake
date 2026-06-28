# Football Sweepstake

A self-hosted football prediction webapp for competing with friends and colleagues. Create a tournament, invite others via a join link, submit your predictions, and watch the leaderboard update in real time as match results come in.

## How does it work?

Create a tournament or join one via an invite link. Make predictions on match scores, group winners, knockout stage winners, and the overall tournament winner. Points are awarded based on how accurate your predictions are — an exact score earns more than just getting the winner right. Each tournament's point values are fully configurable by its admin.

**Features:**
- Create a tournament or join one via a shareable invite link
- Predict match scores, group winners, knockout stage winners, and the overall tournament winner
- Configurable point system per tournament (exact score, correct winner, group winner, stage winner, tournament podium)
- Import tournament fixtures and results automatically from [football-data.org](https://www.football-data.org/)
- Leaderboard showing participants' current rankings and points breakdown
- AI-assisted "lucky dip" — generate Poisson-model predictions with a single click
- Fully responsive: iPhone portrait → 4K landscape
- Light and dark mode (follows OS preference)
- Optional email notifications via SMTP
- Optional error monitoring via [Sentry](https://sentry.io/)

### Tournament Overview
![Preview Overview](/docs/imgs/page_1-overview.png)

### Admin Edit SweepStake
![Preview Edit SweepStake](/docs/imgs/page_1-overview-edit_competition.png)

### Leaderboard
![Preview Leaderboard](/docs/imgs/page_2-leaderboard.png)

### Place Predictions (all pages have light/dark mode)
![Preview Place Predictions](/docs/imgs/page_3-predictions-combined.png)

### Smartphone Optimized (all pages are responsive)
![Preview Smartphone Place Predictions](/docs/imgs/page_3-predictions-smartphone.png)

### View Friends' Predictions
![Preview Friends Predictions](/docs/imgs/popup-match_predictions.png)


<div align="center">

If you like <b>SweepStake</b>, consider giving it a **star** ⭐!  
Made with ❤️ in London  

<a href='https://ko-fi.com/vanalmsick' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi1.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>  
</div>

## Give it a quick try

```sh
docker run -p 80:80 -e DEMO_MODE=true vanalmsick/sweepstake
```

> **Note:** SQLite is fine for a quick try. Use PostgreSQL for anything persistent.


## Full Production Deployment

**[docker-compose.yml](/docker-compose.yml)**

```yaml
services:

  db:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: sweepstake
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d sweepstake"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 10s

  app:
    image: vanalmsick/sweepstake
    restart: unless-stopped
    ports:
      - "80:80"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - migrations_data:/app/data/db_migrations
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/sweepstake
      SECRET_KEY: change-me-to-a-long-random-string
      ROOT_PATH: /api
      HTTPS_AUTH_ONLY: "true"   # set to "false" if not behind TLS
      GUNICORN_WORKERS: "3"     # rule of thumb: (2 × CPU cores) + 1

      # Optional — remove lines you don't need
      EMAIL_HOST: smtp.example.com
      EMAIL_PORT: "587"
      EMAIL_HOST_USER: noreply@example.com
      EMAIL_HOST_PASSWORD: your-smtp-password
      EMAIL_FROM: noreply@example.com
      EMAIL_USE_TLS: "true"
      EMAIL_USE_SSL: "false"
      FOOTBALL_DATA_ORG_API_KEY: ""
      SENTRY_DSN: ""

volumes:
  postgres_data:
  migrations_data:
```

```sh
docker compose -f /path/to/docker-compose.yml up -d
```

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `TZ` | `UTC` | IANA timezone string (e.g. `Europe/London`). Sets the OS clock for nginx/supervisord/PostgreSQL logs and the APScheduler daily-job timezone. |
| `SECRET_KEY` | *(dev placeholder)* | Secret used to sign JWT tokens. **Change this before deploying.** |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/sweepstake` | SQLAlchemy async database URL. |
| `HTTPS_AUTH_ONLY` | `true` | Adds the `Secure` flag to auth cookies. Set to `false` when testing over plain HTTP. |
| `ROOT_PATH` | `""` | FastAPI mount prefix. Set to `/api` when running behind nginx (as in the Docker image). |
| `PORT` | `8888` | Internal port gunicorn listens on (nginx proxies to this). |
| `DEBUG` | `false` | Enable FastAPI debug mode. |
| `LOAD_TEST_DATA` | `false` | Seed the database with sample data on startup. Useful for demos; do not use in production. |
| `GUNICORN_WORKERS` | `2` | Number of gunicorn worker processes. Rule of thumb: `(2 × CPU cores) + 1`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT access token lifetime in minutes. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | JWT refresh token lifetime in days. |
| `HOSTS` | `["http://localhost:3000","http://localhost:5173"]` | Allowed CORS origins (JSON array or comma-separated). |
| `MAIN_HOST` | `http://localhost:3000` | Base URL used to build links in emails. |
| `EMAIL_HOST` | `""` | SMTP server hostname. Leave empty to disable emails. |
| `EMAIL_PORT` | `587` | SMTP server port. |
| `EMAIL_HOST_USER` | `""` | SMTP username. |
| `EMAIL_HOST_PASSWORD` | `""` | SMTP password. |
| `EMAIL_FROM` | `noreply@example.com` | Sender address for outgoing emails. |
| `EMAIL_USE_TLS` | `true` | Use STARTTLS after connecting. Typical for port 587. |
| `EMAIL_USE_SSL` | `false` | Use SMTP_SSL (implicit TLS). Typical for port 465. When `true`, `EMAIL_USE_TLS` is ignored. |
| `FOOTBALL_DATA_ORG_API_KEY` | `""` | [football-data.org](https://www.football-data.org/) API key for importing fixtures and results. |
| `FOOTBALL_DATA_ORG_API_TIER` | `TIER_ONE` | API tier for rate-limit handling (`TIER_ONE`–`TIER_FOUR`). |
| `SENTRY_DSN` | `""` | [Sentry](https://sentry.io/) DSN for error monitoring (backend + frontend). Leave empty to disable. |
| `ONLY_SUPERUSERS_CAN_CREATE_TOURNAMENTS` | `false` | When `true`, only superusers may create new tournaments. Use `manage.py promote_superuser <user_id>` to grant superuser status. |


### Management CLI

The container ships a management CLI at `backend/src/manage.py`. Shell in first:

```sh
docker exec -it sweepstake-app bash
cd /app/backend
/venv/bin/python src/manage.py shell
```

```
SweepStake shell  (type exit() or Ctrl-D to quit)

>>> query(User)                          # list all users
>>> query(Tournament)                    # list all tournaments (incl. participants, matches, …)
>>> query(TournamentParticipantLink)     # all tournament↔user participation rows
>>> get_user_by_id(1)                    # fetch a single user
>>> get_user_by_email("alice@example.com")
>>> get_tournament_by_id(2)
>>> get_user_tournaments(1)              # tournaments a user participates in

>>> welcome_email(tournament_id, user_id)        # trigger a management command from the shell
>>> upcoming_reminders()                          # run the upcoming-matches reminder job now
>>> update_tournament()                           # import/refresh all tournaments from football-data.org
>>> update_tournament(tournament_id)              # import/refresh one tournament from football-data.org
>>> promote_superuser(user_id)                    # grant superuser privileges to a user
>>> promote_superuser(user_id, demote=True)       # revoke superuser privileges
```

For custom queries use `run()` to execute any coroutine:

```python
>>> run(db.execute(select(User).where(User.id == 1))).scalars().all()
>>> run(db.execute(select(TournamentParticipantLink).where(TournamentParticipantLink.user_id == 1))).scalars().all()
```

#### One-liner without entering the container

```sh
# One-liner without entering the container
docker exec sweepstake-app bash -c "cd /app/backend && /venv/bin/python /app/backend/src/manage.py welcome_email 42 7"
docker exec sweepstake-app bash -c "cd /app/backend && /venv/bin/python /app/backend/src/manage.py upcoming_reminders"
docker exec sweepstake-app bash -c "cd /app/backend && /venv/bin/python /app/backend/src/manage.py update_tournament"
docker exec sweepstake-app bash -c "cd /app/backend && /venv/bin/python /app/backend/src/manage.py update_tournament 1"
docker exec sweepstake-app bash -c "cd /app/backend && /venv/bin/python /app/backend/src/manage.py promote_superuser 42"
docker exec sweepstake-app bash -c "cd /app/backend && /venv/bin/python /app/backend/src/manage.py promote_superuser 42 --demote"
```


## Do you want to help / contribute?

### Code overview

```
sweepstake/
├── backend/
│   ├── src/
│   │   ├── tournaments/       # Tournament CRUD, join codes, point config
│   │   ├── matches/           # Match fixtures and results
│   │   ├── groups_stages/     # Group and knockout stage management
│   │   ├── predictions/       # Prediction storage and point calculation
│   │   ├── teams/             # Team data
│   │   ├── users/             # Auth, accounts, password reset, email
│   │   ├── stats/             # Leaderboard and scoring aggregates
│   │   └── api_football_data/  # folder for apis to sync tournament data automatically (e.g. from football-data.org)
│   └── tests/
├── frontend/
│   └── src/
│       ├── pages/             # HomePage, TournamentPage, PredictionsPage, LeaderboardPage
│       ├── api/               # RTK Query endpoints per domain
│       ├── types/             # TypeScript types mirroring backend schemas
│       └── store/             # Redux store, auth slice, listener middleware
├── data/
│   ├── .env.example           # Copy to .env and fill in values
│   └── db_migrations/         # Auto-generated Alembic migration files (gitignored)
├── Dockerfile                 # Multi-stage build (Node → Python deps → runtime)
├── docker-compose.yml
├── nginx.conf                 # Serves SPA, proxies /api/ → gunicorn
└── supervisord.conf           # Manages nginx + gunicorn inside the container
```

**Tech stack**
- **Backend:** FastAPI · SQLModel · Alembic (auto-migrations on startup) · PostgreSQL
- **Frontend:** React · TypeScript · Vite · Redux Toolkit · RTK Query · Tailwind CSS
- **Deployment:** Single container — nginx serves the SPA and proxies `/api/` to gunicorn; supervisord manages both processes

### Running locally for development

#### Backend

```sh
# From the project root
cp data/.env.example data/.env
# Edit data/.env — at minimum set HTTPS_AUTH_ONLY=false and point DATABASE_URL to a local Postgres

cd backend
python -m uvicorn src.main:app --reload --port 8888
# API docs: http://localhost:8888/docs
```

#### Frontend

```sh
cd frontend
echo "VITE_API_BASE_URL=http://localhost:8888/" > .env.local
npm install
npm run dev
# App: http://localhost:5173
```

#### Tests

```sh
cd backend
pytest tests/
```

#### Importing fixtures from football-data.org

1. Get a free API key at [football-data.org](https://www.football-data.org/)
2. Set `FOOTBALL_DATA_ORG_API_KEY` in `data/.env`
3. Use the admin endpoints at `GET /api/football-data-org/tournaments` to list available competitions, then `POST /api/football-data-org/import/{id}` to import one


### ToDos:
- Add automated emails
- Add change password page
- Add reset password email
- Add admin transparency logs

