from django.contrib import admin
from django.urls import path
from playground.views import home, health, compile_regex, simulate_regex

urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("api/v1/health/", health),
    path("api/v1/automata/compile/", compile_regex),
    path("api/v1/automata/simulate/", simulate_regex),
]
