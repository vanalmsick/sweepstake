find . -path "./*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "./data/db_migrations/*" -delete
find /opt/miniconda3/envs/pydev/ -path "*/site-packages/migrations/*.py" -not -name "__init__.py" -delete
find /opt/miniconda3/envs/pydev/ -path "*/site-packages/django/contrib/*/migrations/*.py" -not -name "__init__.py" -delete
find . | grep -E "(__pycache__|\.pyc|\.pyo|\.sqlite3)" | xargs rm -rf