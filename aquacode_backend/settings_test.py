from .settings import *

# las pruebas usan una base en memoria, no usa la de supabase, y jamas deberia!!
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}

PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']