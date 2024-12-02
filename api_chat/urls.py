# api_chat/urls.py
from django.urls import path
from .views import chatbot_kommunicate, verificar_usuario_chat

urlpatterns = [
    path('', chatbot_kommunicate, name='chat_view'),
    path('verificar/', verificar_usuario_chat, name='verificar_chat'),
]
