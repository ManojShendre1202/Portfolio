from django.urls import path
from api.core import views

urlpatterns = [
    path('upload/',          views.uploadDocument),
    path('job/<int:job_id>/', views.getJob),
    path('jobs/',            views.getJobsByClient),
]
