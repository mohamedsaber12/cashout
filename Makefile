build:
	docker-compose build && sudo docker-compose up
up:
	docker-compose up
shell:
	docker-compose exec payouts ./manage.py shell_plus --ipython
makemigrations:
	docker-compose exec payouts ./manage.py makemigrations
showmigrations:
	docker-compose exec payouts ./manage.py showmigrations
migrate:
	docker-compose exec payouts ./manage.py migrate
manage:
	docker-compose exec payouts ./manage.py $(m)
test:
	docker-compose exec payouts ./manage.py test --parallel
superuser:
	docker-compose exec payouts ./manage.py createsuperuser

createcachetable:
	sudo docker-compose exec payouts ./manage.py createcachetable