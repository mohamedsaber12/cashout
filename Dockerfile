FROM python:3.7
MAINTAINER Mohamed Mamdouh && Abobakr

# Create and Set the working directory and the Static&Media Dirs
RUN mkdir -p /home/app
ENV HOME=/home/app
ENV PAYOUTS_HOME=/home/app/payouts_portal
RUN mkdir $PAYOUTS_HOME
RUN mkdir $HOME/static_media
RUN mkdir $HOME/static_media/static
RUN mkdir $HOME/static_media/media
RUN mkdir -p $HOME/static_media/docs/static/mkdocs_build
WORKDIR $PAYOUTS_HOME
# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV LANG C.UTF-8
# Install the requirements
RUN apt-get update && apt-get install -y net-tools
RUN apt-get install nano
#RUN pip install --upgrade pip
#RUN pip install uwsgi #flask supervisor
#RUN pip install --upgrade django-extensions
#COPY ./supervisord.conf /etc/supervisord.conf
#RUN mkdir uwsgi-logs
#RUN touch uwsgi-logs/reqlog.log
#RUN touch uwsgi-logs/errlog.log
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
#RUN mkdir ./logs && mkdir ./logs/uwsgi_logs && mkdir ./logs/celery_logs
COPY ./media/entities_logo/pm_name.png /app/mediafiles/media/entities_logo
COPY ./media/avatars/user.png /app/mediafiles/media/avatars
#COPY ./media/*.png /home/app/static_media/media/
# RUN cd $PAYOUTS_HOME && git submodule update --init
# RUN cd $PAYOUTS_HOME/core && git submodule update --init
# RUN cd $PAYOUTS_HOME && ./scripts/update-submodules.sh
# Creating app user
RUN useradd payouts_user
RUN chown -R payouts_user:payouts_user $HOME
RUN chmod -R 755 $HOME
#USER root
RUN mkdir -p /home/payouts_user/.ssh
RUN chown -R payouts_user:payouts_user /home/payouts_user/.ssh
RUN chown -R payouts_user:payouts_user /app/mediafiles
USER payouts_user
# Copy and run the entrypoint script
#COPY ./entrypoint.sh .
RUN chmod +x ./entrypoint.sh
#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
ENTRYPOINT ["./entrypoint.sh"]
