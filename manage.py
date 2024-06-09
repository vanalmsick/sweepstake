#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Django's command-line utility for administrative tasks."""

import os
import sys
import datetime


def __ensure_db_migration_folders_exist():
    """Ensure that init files exist in the data dir for the migration files."""
    init_files = [
        "data/__init__.py",
        "data/db_migrations/__init__.py",
        "data/db_migrations/general/__init__.py",
        "data/db_migrations/competition/__init__.py",
        # "data/db_migrations/django_celery_beat/__init__.py",
        "data/db_migrations/sessions/__init__.py",
        "data/db_migrations/auth/__init__.py",
        "data/db_migrations/authtoken/__init__.py",
        "data/db_migrations/admin/__init__.py",
        "data/db_migrations/contenttypes/__init__.py",
    ]

    if all([os.path.isfile(i) for i in init_files]) is False:
        for i in init_files:
            dir_only = "/".join(i.split("/")[:-1])
            os.makedirs(dir_only, exist_ok=True)
            open(i, "a").close()


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sweepstake.settings")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    INITIAL_ARGV = sys.argv.copy()

    __ensure_db_migration_folders_exist()

    if os.environ.get("RUN_MAIN", "false") == "false":
        print("Django Server was started at: " f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}")

        # Make data model migrations
        sys.argv = [INITIAL_ARGV[0], "makemigrations"]
        main()

        # Apply data model migrations
        sys.argv = [INITIAL_ARGV[0], "migrate"]
        main()

        # Create Admin
        from general.models import CustomUser

        if len(CustomUser.objects.filter(email="admin@admin.local")) == 0:
            print('Create super user "admin"')
            CustomUser.objects.create_superuser(email="admin@admin.local", password="password")

        # Load EURO 2024 if empty data
        from competition.models import Tournament

        if len(Tournament.objects.all()) == 0:
            print("Add EURO 2024 data")
            sys.argv = [INITIAL_ARGV[0], "add_EURO_2024_data"]
            main()

            if os.environ.get("DEBUG", "True").lower() == "true":
                print("Add test data")
                sys.argv = [INITIAL_ARGV[0], "add_test_data"]
                main()

        # Collect static files
        print("Collect static files")
        sys.argv = [INITIAL_ARGV[0], "collectstatic"]

    else:
        print(
            "Django auto-reloader process executes second instance of django. "
            "Please turn-off for production usage by executing: "
            '"python manage.py runserver --noreload"'
        )

    # Run server
    sys.argv = INITIAL_ARGV
    main()
