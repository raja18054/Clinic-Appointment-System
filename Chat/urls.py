from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('chat/<int:room_id>/', views.room_view, name='room'),
    path('chat/start/<int:user_id>/', views.start_private_chat, name='start_private_chat'),
    path('chat/create-group/', views.create_group_view, name='create_group'),
    path('profile/', views.profile_view, name='profile'),
    path('api/notifications/', views.api_notifications, name='api_notifications'),
    path('api/notifications/read/', views.api_mark_notifications_read, name='api_notifications_read'),
    path('api/user-status/<int:user_id>/', views.api_user_status, name='api_user_status'),
    path('api/search-users/', views.api_search_users, name='api_search_users'),
]
