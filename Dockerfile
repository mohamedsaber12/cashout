# Base upon Python 3.7 image
FROM python:3.7
MAINTAINER Mohamed Mamdouh

# Set default environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create and Set the working directory
RUN mkdir /app \
    && mkdir /app/payouts_portal

# Set project specific environment variables
ENV HOME=/app
ENV PAYOUTS_HOME=/app/payouts_portal
WORKDIR $PAYOUTS_HOME

# Create media and static directories
RUN mkdir -p $HOME/staticfiles/static \
    && mkdir -p $HOME/mediafiles/mkdocs/build \
    && mkdir -p $HOME/mediafiles/media/avatars \
    && mkdir -p $HOME/mediafiles/media/certificates \
    && mkdir -p $HOME/mediafiles/media/transfer_request_attach \
    && mkdir $HOME/mediafiles/media/entities_logo \
    && mkdir -p $HOME/mediafiles/media/documents/disbursement \
    && mkdir $HOME/mediafiles/media/documents/files_uploaded \
    && mkdir $HOME/mediafiles/media/documents/instant_transactions \
    && mkdir $HOME/mediafiles/media/documents/weekly_reports \
    && mkdir -p $PAYOUTS_HOME/logs/uwsgi-logs \
    && mkdir $PAYOUTS_HOME/logs/celery_logs \
    && touch $PAYOUTS_HOME/logs/celery_logs/celery.log
RUN mkdir -p /var/www/docs/static/mkdocs_build
# Install environment dependencies
COPY ./requirements/requirements.txt .
RUN pip3 install --upgrade pip \
    && pip3 install --no-cache-dir -r requirements.txt --no-deps

## Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tzdata \
        python3-setuptools \
        python3-pip \
        python3-dev \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Add the current working directory code to the container's working directory
ADD . $PAYOUTS_HOME/
COPY ./media/entities_logo/pm_name.png /app/mediafiles/media/entities_logo
COPY ./media/avatars/user.png /app/mediafiles/media/avatars

# Creating app user
RUN useradd payouts_user \
    && chown -R payouts_user:payouts_user $HOME && chmod -R 755 $HOME
RUN  chown -R payouts_user:payouts_user /var/ -R && chmod -R 755 /var/www/docs/static/mkdocs_build

RUN chown -R payouts_user:payouts_user $PAYOUTS_HOME

# Copy and run the entrypoint script
COPY ./entrypoint.sh .
RUN chmod 755 entrypoint.sh
ENTRYPOINT ["sh", "/app/payouts_portal/entrypoint.sh"]

#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# Switch to app user
# USER payouts_user
