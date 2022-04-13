build:
	sudo docker-compose build && sudo docker-compose up
up:
	sudo docker-compose up
shell:
	sudo docker-compose exec payouts ./manage.py shell_plus --ipython
makemigrations:
	sudo docker-compose exec payouts ./manage.py makemigrations
showmigrations:
	sudo docker-compose exec payouts ./manage.py showmigrations
migrate:
	sudo docker-compose exec payouts ./manage.py migrate
manage:
	sudo docker-compose exec payouts ./manage.py $(m)
test:
	sudo docker-compose exec payouts ./manage.py test --parallel 
superuser:
	sudo docker-compose exec payouts ./manage.py createsuperuser