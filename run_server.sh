python manage.py runserver
rabbitmq-server start
celery worker -A frontend.analysis.celery --loglevel=info
