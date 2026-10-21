from django.contrib import admin
from django.urls import path
from playground.views import (
    home, health, compile_regex, simulate_regex, csrf_bootstrap,
    account_me, account_register, account_login, account_logout,
    saved_patterns, saved_pattern_detail,
)

urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("api/v1/health/", health, name="health"),
    path("api/v1/automata/compile/", compile_regex, name="compile-regex"),
    path("api/v1/automata/simulate/", simulate_regex, name="simulate-regex"),
    path("api/v1/auth/csrf/", csrf_bootstrap, name="csrf-bootstrap"),
    path("api/v1/auth/me/", account_me, name="account-me"),
    path("api/v1/auth/register/", account_register, name="account-register"),
    path("api/v1/auth/login/", account_login, name="account-login"),
    path("api/v1/auth/logout/", account_logout, name="account-logout"),
    path("api/v1/patterns/", saved_patterns, name="saved-patterns"),
    path("api/v1/patterns/<int:pattern_id>/", saved_pattern_detail, name="saved-pattern-detail"),
]
