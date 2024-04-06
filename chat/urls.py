from django.urls import path, include

from . import views

urlpatterns = [
    path("chat/", views.chat, name="chat-page"),
]
