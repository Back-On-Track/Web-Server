# -*- coding: utf-8 -*-

ALLOWED_HOSTS = ['*']

SECRET_KEY = '0h@p1(0e%*b9r4k+dnpc+7s18lpap6+=cu^#^d=hll+38zv_)r'

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
)

ROOT_URLCONF = 'backontrack.urls'

INSTALLED_APPS = (
    'django.contrib.contenttypes',
)
