from django.urls import path

from . import views

app_name = "dashboard_analytics"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("impact-analytics/", views.impact_analytics, name="impact_analytics"),
    path("api/dashboard/", views.dashboard_data_api, name="dashboard_data_api"),
    path("walking-activities/", views.walking_activity_list, name="walking_activity_list"),
    path("api/walking-activities/", views.walking_activities_api, name="walking_activities_api"),
    path("api/walking-activities/add/", views.create_walking_activity, name="create_walking_activity"),
    path("api/walking-activities/<int:pk>/update/", views.update_walking_activity, name="update_walking_activity"),
    path("api/walking-activities/<int:pk>/delete/", views.delete_walking_activity, name="delete_walking_activity"),
    path("api/budget/", views.save_weekly_budget, name="save_weekly_budget"),
    path("api/habits/", views.add_habit_entry, name="add_habit_entry"),
    path("impact-analytics/report.csv", views.download_report, name="download_report"),
    path("api/impact/", views.add_impact_entry, name="add_impact_entry"),
    path("api/community/comments/", views.community_comments_api, name="community_comments_api"),
    path("api/community/comments/add/", views.add_community_comment, name="add_community_comment"),
    path("api/community/comments/<int:pk>/delete/", views.delete_community_comment, name="delete_community_comment"),
]
