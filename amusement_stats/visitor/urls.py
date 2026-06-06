from django.urls import path

from . import views

urlpatterns = [
    path("", views.visitor_index, name="visitor_index"),
    path("account/", views.visitor_account, name="visitor_account"),
    path("favorites/toggle/", views.visitor_toggle_favorite, name="visitor_favorite_toggle"),
    path("favorites/", views.visitor_favorites, name="visitor_favorites"),
    path("feedback/", views.visitor_feedback, name="visitor_feedback"),
    path("projects/", views.visitor_project_list, name="visitor_project_list"),
    path("projects/<int:project_id>/", views.visitor_project_detail, name="visitor_project_detail"),
    path("itinerary/", views.visitor_itinerary, name="visitor_itinerary"),
    path("itinerary/<int:plan_id>/", views.visitor_itinerary_detail, name="visitor_itinerary_detail"),
    path("recommend/", views.visitor_recommendations, name="visitor_recommend"),
    path("recommend/result/", views.visitor_recommendations, name="visitor_recommend_result"),
    path("recommendations/", views.visitor_recommendations, name="visitor_recommendations"),
    path("analytics/", views.visitor_analytics, name="visitor_analytics"),
    path("map/", views.visitor_map, name="visitor_map"),
    path("api/hot/", views.visitor_api_hot, name="visitor_api_hot"),
    path("api/recommendations/", views.visitor_api_recommendations, name="visitor_api_recommendations"),
]
