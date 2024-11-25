from django.urls import path
from .views import chatbot_kommunicate#, webhook_prueba

urlpatterns = [
    path('', chatbot_kommunicate, name='chat_view'),
    #path('', webhook_prueba, name='chat_view'),
]
