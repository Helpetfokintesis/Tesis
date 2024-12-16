# api_chat/urls.py
from django.urls import path
from .views import chatbot_interaccion, verify_email

urlpatterns = [
    path('interact/', chatbot_interaccion, name='chatbot_interaccion'),
    path('verify-email/', verify_email, name='verify_email'),
]
