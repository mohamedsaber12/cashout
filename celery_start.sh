#!/bin/sh

celery multi restart worker1 --app=payouts.settings --events --beat --scheduler=django --loglevel=info \
 --pidfile="$PWD/var/run/celery/%n.pid" \
 --logfile="$PWD/logs/celery_logs/$(date +'%Y_%m_%d_%I_%M_%p').log" \
&& celery multi restart ach_worker1 --app=payouts.settings --events --scheduler=django --loglevel=info --queue=ach_queue \
 --pidfile="$PWD/var/run/celery/%n.pid" \
 --logfile="$PWD/logs/celery_logs/ach_$(date +'%Y_%m_%d_%I_%M_%p').log" \
&& echo '***** Celery is up now *****'
