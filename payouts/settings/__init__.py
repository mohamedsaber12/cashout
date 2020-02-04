
import environ

ROOT_DIR = environ.Path(__file__) - 3

env = environ.Env()
env.read_env(str(ROOT_DIR.path('.env')))
environment = env.str('ENVIRONMENT')
SECRET_KEY = env.str('SECRET_KEY')
if environment == 'local':
    from .local import *

elif environment == 'staging':
    from .staging import *

else:
    from .production import *

from .celery import app as celery_app

__all__ = ['celery_app']
