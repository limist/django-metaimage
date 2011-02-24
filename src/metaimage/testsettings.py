DATABASES = {
    'default': {
        'ENGINE': 'sqlite3',
        'NAME': '/tmp/metaimage.db'}
    }

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'metaimage',
    'photologue',
    'tagging',
    'uni_form')

METAIMAGE_MAX_REMOTE_IMAGE_SIZE = 1048576  # 1 MB

ROOT_URLCONF = 'metaimage.urls'
