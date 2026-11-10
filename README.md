# GoCluj

Discover upcoming events in Cluj-Napoca in one place, collected daily from ticketing and event websites. Save them, see what your friends are going to, and plan hangouts.

| Part | Tech | Folder |
|---|---|---|
| Frontend | React 19 + Vite | [`frontend/`](frontend/) |
| Backend | FastAPI + SQLAlchemy | [`backend/`](backend/) |
| Database | PostgreSQL 15 (+ pgAdmin) | [`data/`](data/) |
| Scrapers | Scrapy | [`scrape/`](scrape/README.md) |

The project plan is in [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md).

---

## Setup guide

Everything runs in Docker, so you don't need Python, Node or PostgreSQL installed on your machine.

### Step 1: Install the prerequisites

| Tool | Why | Get it |
|---|---|---|
| **Git** | To clone the code | https://git-scm.com/downloads |
| **Docker Desktop** (includes Docker Compose) | Runs every service | https://www.docker.com/products/docker-desktop |
| A code editor (e.g. VS Code) | To edit code | https://code.visualstudio.com |

Docker Desktop must be **running** (the whale icon is in the system tray). On Windows, enable the WSL 2 backend when the installer asks.

Check that everything is installed:

```bash
git --version
docker --version
docker compose version
```

### Step 2: Clone the repository

```bash
git clone https://github.com/N0TB3RT/GoCluj.git
cd GoCluj
```

### Step 3: Create your `.env` file

The services read their settings (database passwords, URLs) from a `.env` file in the project root. Start from the example:

```bash
cp .env.example .env
```

On Windows PowerShell, use `Copy-Item .env.example .env`.

Open `.env` and change the `change-me` passwords. If you change `POSTGRES_USER`, `POSTGRES_PASSWORD` or `POSTGRES_DB`, update `DATABASE_URL` to match. Its format is:

```
postgresql+psycopg2://<POSTGRES_USER>:<POSTGRES_PASSWORD>@db:5432/<POSTGRES_DB>
```

Set the scraper ingest settings so scraped events reach the backend:

```
INGEST_TOKEN=<random value, e.g. from `openssl rand -hex 24`>
INGEST_URL=http://backend:8000/api/ingest/events
```

> `.env` is gitignored. Never commit it.

### Step 4: Start the project

```bash
docker compose up --build -V
```

`-V` recreates anonymous volumes so the frontend's `node_modules` is rebuilt after dependency changes. The first run takes a few minutes while Docker downloads the images and installs the dependencies. Later starts are fast. Leave this terminal open: it shows the logs from every service. Stop everything with `Ctrl+C`.

To run it in the background instead, use `docker compose up --build -d` and stop it with `docker compose down`.

### Step 5: Open the apps

| What | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API docs (Swagger) | http://localhost:8000/docs |
| pgAdmin (database UI) | http://localhost:5050 |

**To connect pgAdmin to the database:**
1. Log in with `PGADMIN_DEFAULT_EMAIL` / `PGADMIN_DEFAULT_PASSWORD` from your `.env`.
2. Right-click **Servers → Register → Server**.
3. On the **General** tab, set any name (e.g. `GoCluj`).
4. On the **Connection** tab, set:
   - host `db`
   - port `5432`
   - the user, password and database from your `.env`

The database tables are created by Alembic migrations, which run automatically every time the backend starts. After a schema change that needs a clean start (or if your local DB was created from the old `schema1.sql`), reset it with `docker compose down -v` (deletes local data).

### Step 6: Run the scrapers (optional)

The scrapers don't start with `docker compose up`. Run them on demand:

```bash
docker compose --profile scraper build scraper
docker compose run --rm scraper
```

To try a single source with one listing page:

```bash
docker compose run --rm scraper python -m scrapy crawl iabilet -a max_pages=1
```

The iaBilet parser is still being written, so for now its run finishes with 0 events and is reported as "failed". That's expected. See [`scrape/README.md`](scrape/README.md) for details and how to add a new source.

### Step 7: Run the tests

Scraper lint and tests run inside a throwaway Python container:

```bash
docker run --rm -v "$PWD/scrape:/app" -w /app python:3.11-slim sh -c \
  "pip install -q -r requirements.txt -r requirements-dev.txt && ruff check . && pytest -q"
```

On Windows Git Bash, prefix the command with `MSYS_NO_PATHCONV=1`. In PowerShell, use `${PWD}/scrape` instead of `$PWD/scrape`.

Backend lint and tests (they use a separate `<POSTGRES_DB>_test` database; the `db` service must be running):

```bash
docker compose run --rm --no-deps backend pytest -q
docker compose run --rm --no-deps backend ruff check .
```

See [`backend/README.md`](backend/README.md). Frontend tests will be added in FE-01.

---

## Day-to-day workflow

1. Get the latest code: `git switch main && git pull`.
2. Create a branch for your task, e.g. `git switch -c feature/<short-name>`.
3. Code. The backend and frontend reload automatically when you save a file.
4. Commit, push and open a pull request into `main`.

If you add a dependency, rebuild that service with `docker compose up --build <service>`. Service names are `backend`, `frontend` and `scraper`.

## Useful commands

| Task | Command |
|---|---|
| Start everything | `docker compose up --build` |
| Stop everything | `docker compose down` |
| See one service's logs | `docker compose logs -f backend` |
| Open a shell in a container | `docker compose exec backend sh` |
| Open a database shell | `docker compose exec db psql -U <POSTGRES_USER> -d <POSTGRES_DB>` |
| **Reset the database** (deletes all data!) | `docker compose down -v`, then `docker compose up --build` |

## Troubleshooting

- **`port is already allocated`:** another program is using port 3000, 8000, 5050 or 5432 (often a local PostgreSQL). Stop that program, or change the left-hand port in `docker-compose.yml` (e.g. `"5433:5432"`).
- **Backend fails with `DATABASE_URL environment variable is not set`:** your `.env` is missing or isn't in the project root. Repeat Step 3.
- **Backend can't connect to the database:** check that the user, password and database name in `DATABASE_URL` match `POSTGRES_*`, and that the host is `db`, not `localhost`.
- **Database tables are missing or outdated after a schema change:** Migrations run on backend start; if the DB still comes from the old `schema1.sql`, reset it (see the table above).
- **`docker: command not found` or "cannot connect to the Docker daemon":** Docker Desktop isn't installed or isn't running.
- **Frontend doesn't reload on Windows:** file polling is already enabled in `vite.config.js`. Restart the service with `docker compose restart frontend`.

## Documentation

- [Implementation plan](docs/IMPLEMENTATION_PLAN.md): goals, epics, sprints, decisions
- [Scraper design](docs/scrape/scraper-design.md): how event collection works and why
- [Scraper README](scrape/README.md): running scrapers and adding a new source
- [Backend README](backend/README.md): API, migrations and tests
