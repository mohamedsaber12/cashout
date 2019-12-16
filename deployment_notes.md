# Depolyment Notes

# Table Of Contents
1. [Deployment Preparation](#deployment-preparation)
2. [Python Installation](#python-installation)
3. [Postgres Installation](#postgres-installation)
4. [Database Set up](#database-set-up)
5. [RabbitMQ Server Installation](#installing-rabbitmq-server)
6. [Nginx Installation](#installing-nginx)
7. [Create Payroll user](#create-payroll-user)
8. [Clone the portal and set it up](#clone-the-portal-and-set-it-up)
9. [Make the migrations](#make-the-migrations)
10. [Change server's host name to meaningful name (Optional)](#change-servers-host-name-to-meaningful-name-optional)
11. [Configure Nginx](#configure-nginx)
12. [Install uwsgi to run the portal](#install-uwsgi-to-run-the-portal)
13. [Handle the static files](#handle-the-static-files)
14. [Encrypt SSL Certificates using Certbot](#install-certbot)
15. [License](#license)


## Deployment Preparation

### Update CentOS

> It is always best to start with an updated operating system.
> use the following command to update CentOS and reboot:

```
$ yum update -y
$ reboot
```


## Python Installation

> Use below set of commands to Download Python source code on your system.

```
$ cd /usr/src

$ wget https://www.python.org/ftp/python/3.7.5/Python-3.7.5.tgz

$ tar xzf Python-3.7.4.tgz
```

> It is necessary to install the gcc compiler if is not in your $PATH. > 

```
$ yum groupinstall "Development Tools"
```

> Use altinstall command to compile Python source code on your system.

```
$ make altinstall

$ reboot
```


## Postgres Installation

```
$ sudo yum install postgresql11.4-server postgresql11.4-contrib
```


## Database Set up

> At ec2-user

```
sudo su - postgres

psql

CREATE DATABASE payroll_database;

CREATE USER payroll_user WITH PASSWORD 'PayrollPortalPassword';

ALTER ROLE payroll_user SET client_encoding TO 'utf8';

ALTER ROLE payroll_user SET default_transaction_isolation TO 'read committed';

ALTER ROLE payroll_user SET timezone TO 'UTC';

GRANT ALL PRIVILEGES ON DATABASE payroll_database TO payroll_user;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public to payroll_user;

GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public to payroll_user;

GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public to payroll_user;

\q

exit          , Exit from psql to ec2-user
```




## RabbitMQ Server Installation


[Installation Notes](http://stevenonofaro.com/rabbitmq-installation-on-centos-7/)


```
sudo systemctl daemon-reload

sudo systemctl start rabbitmq-server

sudo systemctl enable rabbitmq-server

sudo rabbitmq-plugins enable rabbitmq_management

sudo chown -R rabbitmq:rabbitmq /var/lib/rabbitmq/
```

> The following three commands can be skipped and instead use the GUEST User

```
sudo rabbitmqctl add_user rabbit_user RabbitUser

sudo rabbitmqctl set_user_tags rabbit_user administrator

sudo rabbitmqctl set_permissions -p / rabbit_user “.*”  “.*”  “.*”
```

## Nginx Installation

```
sudo yum install nginx

ps aux | grep nginx

sudo service nginx start

sudo systemctl enable nginx

sudo systemctl restart nginx
```


## Create Payroll user

```
yum install -y git

useradd payroll-user

useradd www-data

usermod -aG www-data payroll-user

usermod -aG ec2-user payroll-user

ls -l /sbin/nologin           Should be no nologin file

usermod --login /sbin/nologin www-data

usermod www-data --login /sbin/nologin

systemctl restart nginx

passwd payroll-user         0a4c401e91524e5988078f9839aa76c4
```



## Clone the portal and set it up

> Switch to Payroll user

```
su - payroll-user

ssh-keygen

cat .ssh/id_rsa.pub

add this public key to the gitlab-ssh-settings

mkdir disbursement-staging

cd disbursement-staging/

git clone git@gitlab.com:MISC-PayMob/disbursment_tool.git

cd disbursment_tool/

vi .env
```

1. Press i
2. Paste the following content

```
ENVIRONMENT=staging
SECRET_KEY=+@j#)!v#a#hi4x4y&x@#y69&_co6#&mp=k+v6y1ghfewor3w&i

DEVELOPMENT=https://4ac3ee9d-b9f6-48de-948e-abc6b33d0bf1.mock.pstmn.io/NewTxn/ServiceSelector
STAGING=https://52.28.129.40:8080/NewTxn/ServiceSelector

EMAIL_HOST_USER=AKIAIBBG4EPQMH72VCEA
EMAIL_HOST_PASSWORD=AmwPtRx02knXLgv+ERiFIE4vAJlA7Gy1oxUbAosUDBLr
CALL_WALLETS=TRUE

DB_NAME=payroll_database
DB_USER=payroll_user
DB_PASSWORD=PayrollPortalPassword

CELERY_BROKER_URL=amqp://guest:guest@localhost:5672/

STATIC_ROOT=/var/www/static/
MEDIA_ROOT=/var/www/media/
```

3. Press :wq

```
cd ..

pip3.7 install --user virtualenv

virtualenv venv

source venv/bin/activate

pip install -r requirements.txt
```


## Make the migrations


> $ python manage.py makemigrations       , make migrations for each app on its own

> $ python manage.py migrate              , migrate each app on its own


```
python manage.py makemigrations users
python manage.py migrate users

python manage.py makemigrations data
python manage.py migrate data

python manage.py makemigrations disb
python manage.py migrate disb

python manage.py makemigrations payment
python manage.py migrate payment

python manage.py makemigrations
python manage.py migrate            migrate third party packages
```


## Change server's host name to meaningful name (Optional)

```
hostnamectl set-hostname payroll-staging

vi /etc/hosts
```
1. Press i

2. Copy&Paste the following       ```18.220.141.7    payroll-staging```

3. Press :wq

```systemctl reload```

```exit              Exit from payroll-user to ec2-user```



## Configure Nginx


> Switch to ec2-user


```
cd

sudo vi /etc/nginx/nginx.conf
```

1. Press i

2. Copy&Paste the following

```
# For more information on configuration, see:
#   * Official English Documentation: http://nginx.org/en/docs/
#   * Official Russian Documentation: http://nginx.org/ru/docs/

user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

# Load dynamic modules. See /usr/share/doc/nginx/README.dynamic.
include /usr/share/nginx/modules/*.conf;

events {
    worker_connections 1024;
}

http {
    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;

    sendfile            on;
    tcp_nopush          on;
    tcp_nodelay         on;
    keepalive_timeout   65;
    types_hash_max_size 2048;

    include             /etc/nginx/mime.types;
    default_type        application/octet-stream;

    # Load modular configuration files from the /etc/nginx/conf.d directory.
    # See http://nginx.org/en/docs/ngx_core_module.html#include
    # for more information.
    include /etc/nginx/conf.d/*.conf;

#    server {
#        listen       80 default_server;
#        listen       [::]:80 default_server;
#        server_name  _;
#        root         /usr/share/nginx/html;

        # Load configuration files for the default server block.
        include /etc/nginx/default.d/*.conf;

 #       location / {
 #       }

#        error_page 404 /404.html;
#            location = /40x.html {
#        }

#        error_page 500 502 503 504 /50x.html;
#            location = /50x.html {
#        }
#    }

# Settings for a TLS enabled server.
#
#    server {
#        listen       443 ssl http2 default_server;
#        listen       [::]:443 ssl http2 default_server;
#        server_name  _;
#        root         /usr/share/nginx/html;
#
#        ssl_certificate "/etc/pki/nginx/server.crt";
#        ssl_certificate_key "/etc/pki/nginx/private/server.key";
#        ssl_session_cache shared:SSL:1m;
#        ssl_session_timeout  10m;
#        ssl_ciphers HIGH:!aNULL:!MD5;
#        ssl_prefer_server_ciphers on;
#
#        # Load configuration files for the default server block.
#        include /etc/nginx/default.d/*.conf;
#
#        location / {
#        }
#
#        error_page 404 /404.html;
#            location = /40x.html {
#        }
#
#        error_page 500 502 503 504 /50x.html;
#            location = /50x.html {
#        }
#    }

}
```

```sudo vim /etc/nginx/conf.d/default.conf```

1. Press i

2. Paste the following


```
iupstream django {
    server 127.0.0.1:8000;
}


server {
   listen 80;
   server_name localhost 127.0.0.1;

        location /media/  {
                root /var/www/media/;
                }

        location /static/ {
                root /var/www/static/;
                }

        location / {
                proxy_set_header Host $host;
                proxy_set_header X-Real-IP $remote_addr;
                proxy_pass  http://django;
                include     /etc/nginx/uwsgi_params; # the uwsgi_params file you installed
                }

}
```

3. Press :wq

```sudo systemctl restart nginx```



## Install uwsgi to run the portal


> Switch to payroll-user


```
sudo su - payroll-user

cd disbursement-staging/

source venv/bin/activate

pip install uwsgi

cd disbursment_tool/

uwsgi -s :8000 -M --env DJANGO_SETTINGS_MODULE=disbursement.settings --chdir"$PWD" -w django.core.wsgi:get_wsgi_application() --chmod-socket=666 --enable-threads --thunder-lock --daemonize /tmp/uwsgi.log --workers 5 -b 32768

uwsgi -i uwsgi.ini
```
```exit             Exit to ec2-user```


> At ec2-user

> Test if it's running ok?

```
curl localhost:80

curl -v http://127.0.0.1/admin/
```

```exit           Exit from payroll-user to ec2-user```



## Handle the static files


> At ec2-user


```
$ cd

$ mkdir /var/www/

$ mkdir /var/www/static/

$ mkdir /var/www/media/
```


> At payroll-user


```
$ sudo su - payroll-user

$ source ~/disbursement-staging/venv/bin/activate

$ cd ~/disbursement-staging/disbursment_tool/

$ python manage.py collectstatic

$ exit                            , Exit from payroll-user to ec2-user
```


> At payroll-user


```
$ sudo chown -R payroll-user:payroll-user /var/www/

$ sudo chmod -Rv 755 /var/www/ 
```



## Encrypt SSL Certificates using Certbot


> If you're using RHEL or Oracle Linux, you'll also need to enable the optional channel


```
$ sudo yum -y install yum-utils

$ sudo yum-config-manager --enable rhui-REGION-rhel-server-extras rhui-REGION-rhel-server-optional

```


> Run this command on the command line on the machine to install Certbot.


```
$ sudo yum install certbot python2-certbot-nginx
```


> Run this command to get a certificate and have Certbot edit your Nginx configuration automatically


```
$ sudo certbot --nginx

$ sudo certbot certonly --nginx

$ sudo systemctl restart nginx
```


> Remove the previous -temporary- Nginx configurations and replace it with the auto-generated one from certbot

```
sudo rm -rfv /etc/nginx/conf.d/default.conf

sudo certbot --nginx --domain payroll.paymobsolutions.com

sudo systemctl restart nginx
```

> Test if it's running ok?

```curl -vk https://0.0.0.0:443/```


### Set up automatic renewal


> We recommend running the following line, which will add a cron job to the default crontab.


```
$ sudo certbot --nginx

$ sudo certbot certonly --nginx

$ sudo systemctl restart nginx
```


## License

