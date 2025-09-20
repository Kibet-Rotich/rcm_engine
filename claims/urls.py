from django.contrib.auth import views as auth_views
from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("upload_claims/", views.upload_claims, name="upload_claims"),
    path("upload_rules/", views.upload_rules, name="upload_rules"),
    path("validate/", views.run_validation, name="run_validation"),
    path("results/", views.claim_results, name="claim_results"),
    path("rules/", views.rule_summary, name="rule_summary"),
    path("charts/", views.charts, name="charts"),


    # Login/logout
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
]
