# =============================================================================
# Stage 1 — Build the React frontend
# =============================================================================
# node:26-slim (Debian) avoids musl-libc incompatibility with native Node
# modules such as lightningcss (used by Tailwind v4 / PostCSS).
FROM node:26-slim AS frontend-build

WORKDIR /app

# Install deps first (separate layer = cached unless package.json changes)
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --prefer-offline

# VITE_API_BASE_URL is baked into the JS bundle at build time.
# In production the React app sends all API calls to /api/ which nginx
# strips and proxies to the FastAPI backend on 127.0.0.1:8888.
ARG VITE_API_BASE_URL=/api/
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY frontend/ .
RUN npm run build


# =============================================================================
# Stage 2 — Install Python dependencies into an isolated virtualenv
# =============================================================================
# Using a venv means Stage 3 only needs to copy /venv — no pip, wheel, or
# setuptools bleed into the final image.
FROM python:3.14.6-slim AS py-deps

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

COPY backend/src/requirements.txt .

# gunicorn is a production process manager not needed in dev, so it lives here
# rather than in requirements.txt.
RUN pip install --no-cache-dir -r requirements.txt gunicorn


# =============================================================================
# Stage 3 — Runtime image
# =============================================================================
# python:3.12-slim (Debian bookworm) gives us the smallest Python base that is
# compatible with all manylinux binary wheels (asyncpg, cryptography, argon2 …).
FROM python:3.14.6-slim AS runtime

# Install nginx + supervisor in a single layer and clean up apt caches
# immediately so they don't bloat the layer.
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        nginx \
        supervisor \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtualenv built in Stage 2
COPY --from=py-deps /venv /venv
ARG APP_VERSION=""
ENV PATH="/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_VERSION=$APP_VERSION \
    GUNICORN_WORKERS=2

# Copy nginx and supervisord configuration
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/sweepstake.conf

# Copy the compiled React app into nginx's web root
COPY --from=frontend-build /app/dist /var/www/html

# Copy the backend application.
# We mirror the local dev directory layout so that alembic's
# relative version_locations path (../data/db_migrations in alembic.ini)
# resolves correctly inside the container:
#   /app/backend/alembic.ini  →  version_locations = ../data/db_migrations
#   /app/data/db_migrations/  ✓
COPY data/ /app/data/
COPY backend/ /app/backend/

# Drop privileges: gunicorn runs as www-data (already the nginx worker user).
# Root is still needed for supervisord to start nginx on port 80, but child
# processes run unprivileged. /var/run is kept root-owned for the supervisord pid.
RUN chown -R www-data:www-data /app /venv /var/www

EXPOSE 80

# Fail fast if the app is unhealthy; docker / compose will restart the container.
HEALTHCHECK --interval=60s --timeout=5s --start-period=30s --retries=5 \
    CMD curl -f -A "Docker-Healthcheck" http://localhost/api/healthcheck || exit 1

CMD ["supervisord", "-n", "-c", "/etc/supervisor/conf.d/sweepstake.conf"]
