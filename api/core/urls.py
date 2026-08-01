from django.urls import path
from api.core import views
from api.core import doc_pages

urlpatterns = [
    path('readar/session/',                        views.getOrCreateSession),
    path('readar/session/new/',                    views.startNewSession),
    path('readar/session/<uuid:chat_id>/turns/',   views.getSessionTurns),
    path('readar/session/<uuid:chat_id>/switch/',  views.switchSession),
    path('readar/session/<uuid:chat_id>/delete/',  views.deleteSession),
    path('readar/sessions/',                        views.listSessions),
    path('readar/doc/<str:doc_id>/page/<str:chapter>/', doc_pages.getDocPage),
]
