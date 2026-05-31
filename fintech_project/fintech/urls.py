# fintech/urls.py
from django.urls import path
from . import views

urlpatterns = [
    
    path('health/', views.health_check, name='health'),
    path('stats/', views.stats, name='stats'),
    path('debug/', views.debug_info, name='debug'),
    
    
    path('slow/', views.test_slow_query, name='slow'),
    path('optimized/', views.test_optimized_query, name='optimized'),
    path('comparison/', views.comparison_view, name='comparison'),
]