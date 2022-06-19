#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

# Switch to payouts_user
# su - payouts_user

# Migrate users app
# python manage.py makemigrations users
# python manage.py migrate users

# Migrate data app
# python manage.py makemigrations data
# python manage.py migrate data

# Migrate disbursement app
# python manage.py makemigrations disbursement
# python manage.py migrate disbursement

# Migrate instant_cashin app
# python manage.py makemigrations instant_cashin
# python manage.py migrate instant_cashin

# Migrate payment app
# python manage.py makemigrations payment
# python manage.py migrate payment

# Migrate utilities app
# python manage.py makemigrations utilities
# python manage.py migrate utilities

# Check for any missing migrations
# python manage.py makemigrations
# python manage.py migrate

# Generate the API documentation static files
# mkdocs build

exec "$@"
