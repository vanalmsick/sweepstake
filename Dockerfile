# syntax=docker/dockerfile:1

FROM python:3.11.9-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install basic packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends lsb-release curl gpg nano netcat-traditional nginx

# Install redis
RUN curl -fsSL https://packages.redis.io/gpg | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/redis.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends redis

# Install pip python packages
COPY requirements.txt /sweepstake/requirements.txt
RUN pip3 install --no-cache-dir -r /sweepstake/requirements.txt

# Add non-root user "app_user"
RUN useradd -U app_user \
    && install -d -m 0755 -o app_user -g app_user /sweepstake
USER app_user:app_user

# Copy code and make dir editable by "app_user"
COPY --chown=app_user:app_user / /sweepstake/

WORKDIR /sweepstake

RUN chown -R app_user:app_user /sweepstake \
    && chmod -R 775 /sweepstake \
    && chmod -R 777 /sweepstake/data

# Add docker container labels
LABEL org.opencontainers.image.title="Sweepstake"
#LABEL org.opencontainers.image.description="News Aggregator - Aggregates news articles from several RSS feeds, fetches full-text if possible, sorts them by relevance (based on user settings), and display on distraction-free homepage."
LABEL org.opencontainers.image.authors="https://github.com/vanalmsick"
LABEL org.opencontainers.image.url="https://github.com/vanalmsick/sweepstake"
#LABEL org.opencontainers.image.documentation="https://vanalmsick.github.io/sweepstake/"
LABEL org.opencontainers.image.source="https://hub.docker.com/r/vanalmsick/sweepstake"
LABEL org.opencontainers.image.licenses="MIT"

# Expose Port: Main website
EXPOSE 80
# Expose Port: Celery Flower - for dev
EXPOSE 5555
# Expose Port: Supervisord - for dev
EXPOSE 9001
# Permanent storage for database and config files
VOLUME /sweepstake/data

# Configure automatic docker container healthcheck
HEALTHCHECK --interval=5m --timeout=60s --retries=3 --start-period=120s \
    CMD echo Successful Docker Container Healthcheck && curl --max-time 30 --connect-timeout 30 --silent --output /dev/null --show-error --fail http://localhost:80/ || exit 1

# Start News Platform using supervisord
CMD ["supervisord", "-c", "./supervisord.conf"]
