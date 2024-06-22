#!/bin/bash

export DJANGO_SETTINGS_MODULE="sweepstake.settings"

echo "Run make migrations"
python manage.py makemigrations

echo "Run migrate"
python manage.py migrate

if [ $DEBUG == "true" ] || [ $DEBUG == "True" ]; then
	echo "Run Django Server"
	python ./manage.py runserver 0.0.0.0:80;
else
	echo "Run Gunicorn Server"
	python manage.py collectstatic --noinput
	cp data/qr_pay.jpg static/qr_pay.jpg || true
	gunicorn -c ./gunicorn.conf.py;
fi
