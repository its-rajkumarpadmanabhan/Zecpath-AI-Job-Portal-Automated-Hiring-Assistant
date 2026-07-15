from django.urls import path

from rest_framework_simplejwt.views import TokenRefreshView
from .views import *

urlpatterns = [

    path('jobs/', JobListAPIView.as_view(), name='job-list'),
    path('jobs/create/', JobCreateAPIView.as_view(), name='job-create'),

    path('applications/create/', ApplicationCreateAPIView.as_view(), name='application-create'),
    path('admin/users/', AdminUserListAPIView.as_view(), name='admin-users'),
    
    path('auth/signup/', SignupAPIView.as_view(), name='signup'),
    path('auth/login/', LoginAPIView.as_view(), name='login'),
    path('auth/logout/', LogoutAPIView.as_view(), name='logout'),

    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
