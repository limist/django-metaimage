DATABASES = {
    'default': {
        'ENGINE': 'sqlite3',
        'NAME': '/tmp/metaimage.db',
        }
    }

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'metaimage',
    'photologue',
    'tagging',
    ]

ROOT_URLCONF = ['metaimage.urls']
