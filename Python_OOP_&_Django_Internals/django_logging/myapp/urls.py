from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('test/', views.test_view, name='test'),
    path('slow/', views.slow_view, name='slow'),
    path('error/', views.error_view, name='error'),
    path('json/', views.json_view, name='json'),
    path('user-agent/', views.user_agent_view, name='user_agent'),
]