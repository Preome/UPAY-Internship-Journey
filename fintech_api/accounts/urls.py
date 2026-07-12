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
]