#!/bin/sh
docker run -p 80:80 -p 5555:5555 -p 9001:9001 --env-file ../data/.env --name sweep_stake --pull=always vanalmsick/sweepstake:dev
