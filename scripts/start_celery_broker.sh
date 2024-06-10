#!/bin/sh
export $(xargs <./data/.env)
celery -A sweepstake worker
