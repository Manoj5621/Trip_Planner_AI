from django.urls import path
from . import views

app_name = 'trips'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('plan/', views.plan_trip, name='plan_trip'),
    path('explore/', views.explore_trips, name='explore_trips'),
    path('saved-trips/', views.saved_trips, name='saved_trips'),
    path('trip/<int:trip_id>/', views.view_trip, name='view_trip'),
    path('trip/<int:trip_id>/rate/', views.rate_trip, name='rate_trip'),
    path('trip/<int:trip_id>/ratings/', views.get_trip_ratings, name='get_trip_ratings'),
    path('trip/<int:trip_id>/post/', views.post_trip, name='post_trip'),
    path('trip/<int:trip_id>/save/', views.save_trip, name='save_trip'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
] 