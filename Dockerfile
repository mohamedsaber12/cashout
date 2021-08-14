FROM python:3.7
MAINTAINER Abobakr

# Create and Set the working directory
RUN mkdir -p /app 


# Create and Set the working directory and the Static&Media Dirs
ENV HOME=/app
ENV PAYOUTS_HOME=/app/payouts_portal


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


WORKDIR $PAYOUTS_HOME


# Set default environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV LANG C.UTF-8

# Install Requirements
RUN apt-get update && apt-get install -y net-tools
RUN apt-get install nano
COPY ./requirements/requirements.txt .
RUN pip3 install --upgrade pip \
       && pip3 install --no-cache-dir -r requirements.txt --no-deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tzdata \
        python3-setuptools \
        python3-pip \
        python3-dev \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


# Copy the portal to the container's working directory
COPY . $PAYOUTS_HOME

COPY ./media/entities_logo/pm_name.png /app/mediafiles/media/entities_logo
COPY ./media/avatars/user.png /app/mediafiles/media/avatars
#COPY ./media/*.png /home/app/static_media/media/
# RUN cd $PAYOUTS_HOME && git submodule update --init
# RUN cd $PAYOUTS_HOME/core && git submodule update --init
# RUN cd $PAYOUTS_HOME && ./scripts/update-submodules.sh


# Modify User permissions
RUN useradd payouts_user
RUN chown -R payouts_user:payouts_user $HOME
RUN chmod -R 755 $HOME
RUN mkdir -p /home/payouts_user/.ssh
RUN chown -R payouts_user:payouts_user /home/payouts_user/.ssh
RUN chown -R payouts_user:payouts_user /app/mediafiles
RUN chown -R payouts_user:payouts_user /app/staticfiles

USER payouts_user
RUN chmod +x ./entrypoint.sh
#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000", "--noreload"]
#ENTRYPOINT ["/app/payouts_portal/entrypoint.sh"]
ENTRYPOINT ["./entrypoint.sh"]
