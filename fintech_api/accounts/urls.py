from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AccountViewSet, 
    TransactionViewSet,
    AccountAPIView,      
    AccountGenericView  
)


router = DefaultRouter()
router.register(r'accounts', AccountViewSet, basename='account')
router.register(r'transactions', TransactionViewSet, basename='transaction')

urlpatterns = [
    
    path('api/', include(router.urls)),
    
   
    path('api-compare/accounts-api/', AccountAPIView.as_view(), name='account-api'),
    path('api-compare/accounts-generic/', AccountGenericView.as_view(), name='account-generic'),
    
    
    path('api-auth/', include('rest_framework.urls')),
]


from . import views_django
urlpatterns += [
    path('django/accounts/', views_django.AccountListView.as_view(), name='django_account_list'),
    path('django/accounts/create/', views_django.AccountCreateView.as_view(), name='django_account_create'),
    path('django/accounts/<int:pk>/update/', views_django.AccountUpdateView.as_view(), name='django_account_update'),
    path('django/accounts/<int:pk>/delete/', views_django.AccountDeleteView.as_view(), name='django_account_delete'),
    path('django/dashboard/', views_django.DashboardView.as_view(), name='django_dashboard'),
]