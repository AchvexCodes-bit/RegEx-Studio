from django.contrib import admin
from django.urls import path
from playground.views import health, compile_regex
urlpatterns = [path('admin/', admin.site.urls), path('api/v1/health/', health), path('api/v1/automata/compile/', compile_regex)]
