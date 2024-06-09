#!/bin/sh
docker run -p 8080:8080 --env-file ./data/.env --name sweep_stake --pull=always vanalmsick/sweepstake:dev
