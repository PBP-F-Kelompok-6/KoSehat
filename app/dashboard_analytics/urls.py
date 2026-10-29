from django.urls import path

from . import views

app_name = "dashboard_analytics"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("impact-analytics/", views.impact_analytics, name="impact_analytics"),
    path("api/dashboard/", views.dashboard_data_api, name="dashboard_data_api"),
    path("api/habits/", views.add_habit_entry, name="add_habit_entry"),
    path("impact-analytics/report.csv", views.download_report, name="download_report"),
    path("api/impact/", views.add_impact_entry, name="add_impact_entry"),
    path("api/community/comments/", views.community_comments_api, name="community_comments_api"),
    path("api/community/comments/add/", views.add_community_comment, name="add_community_comment"),
]
