from django.urls import path
from api.core import views
from api.core import doc_pages
from api.core import admin_views

urlpatterns = [
    path('readar/session/',                        views.getOrCreateSession),
    path('readar/session/new/',                    views.startNewSession),
    path('readar/session/<uuid:chat_id>/turns/',   views.getSessionTurns),
    path('readar/session/<uuid:chat_id>/switch/',  views.switchSession),
    path('readar/session/<uuid:chat_id>/delete/',  views.deleteSession),
    path('readar/sessions/',                        views.listSessions),
    path('readar/doc/<str:doc_id>/page/<str:chapter>/', doc_pages.getDocPage),
    path('readar/admin-dashboard/',                admin_views.admin_dashboard),
    path('readar/admin-dashboard/stats/',          admin_views.admin_stats),
    path('readar/admin-dashboard/logs/',           admin_views.admin_logs),
]
