DATABASES = {
    'default':   {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'plantedge_iono',
        # 'NAME': 'plantedge',

        # 'USER': 'postgres',
        'USER': 'iono_labs',
        'PASSWORD': '12345',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

DEBUG = True
ALLOWED_HOSTS = ['*']
