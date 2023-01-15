# Broker settings.
BROKER_URL = 'redis://127.0.0.1:6379/0'

# List of modules to import when celery starts.
CELERY_IMPORTS = ('tasks', )

# Using the database to store task state and results.
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/1'

CELERY_TASK_RESULT_EXPIRES = 18000

CELERYD_CONCURRENCY = 4

CELERY_ACCEPT_CONTENT = ['pickle', 'json', 'msgpack', 'yaml']
