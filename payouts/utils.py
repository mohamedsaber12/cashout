
def get_dot_env():
    from django.conf import settings
    import os
    import environ

    env = environ.Env()
    environ.Env.read_env(env_file=os.path.join(settings.BASE_DIR, '.env'))

    return env
