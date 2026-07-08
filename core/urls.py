from django.urls import path
from .views import JobListAPIView, JobCreateAPIView, UserTestAPIView

urlpatterns = [
   
    path('jobs/', JobListAPIView.as_view(), name='job-list'),
    path('jobs/create/', JobCreateAPIView.as_view(), name='job-create'),
    path('users/', UserTestAPIView.as_view(), name='user-test'),
]
