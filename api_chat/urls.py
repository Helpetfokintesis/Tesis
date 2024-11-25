from django.urls import path
from .views import chatbot_kommunicate, verificar_usuario_json
urlpatterns = [
    path('', chatbot_kommunicate, name='chat_view'),
    path('verificar_usuario/', verificar_usuario_json, name='verificar_usuario'),

]
