#!/bin/sh
docker run -p 5432:5432 -e POSTGRES_PASSWORD="postgres" -d --name sweep-stake-postgres postgres:16
docker run -p 80:80 -p 5555:5555 -p 9001:9001 --env-file ../data/.env --name sweep-stake --pull=always vanalmsick/sweepstake:dev
