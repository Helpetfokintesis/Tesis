"""
URL configuration for helpet project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import handler404, handler403,handler500
from app import views
from rest_framework.documentation import include_docs_urls


urlpatterns = [

    path('admin/', admin.site.urls),
    path('', views.index, name = "index"),
    path('iniciarSesion', views.iniciarSesion, name='iniciarSesion'),
    path('cerrarSesion', views.cerrarSesion, name='cerrarSesion'),
    path('registro', views.registro, name = "registro"),
    path('registroUsuario', views.registro_usuario, name = "registroUsuario"),
    path('recordatorios', views.recordatorios, name="recordatorios"),

    path('eliminarRecordatorio/<uuid:id_recordatorio>/', views.eliminar_recordatorio, name="eliminar_recordatorio"),
    path('agregarRecordatorio/<uuid:id_mascota>/', views.agregar_recordatorio, name="agregar_recordatorio"),
    path('marcar_completado/<uuid:id_recordatorio>/', views.marcar_completado, name="marcar_completado"),

    #chat prueba    
    path('chat/', include('api_chat.urls')),
    path('api/', include('app.urls')),
    path('docs/', include_docs_urls(title = 'API Documentation')),

    #paths nico :)
    path('dashboard', views.dashboard, name= 'dashboard'),
    path('agenda', views.agenda, name= 'agenda'),
    path('agregar_producto/', views.agregar_producto, name='agregar_producto'),
    path('visualizar_productos/', views.visualizar_productos, name='visualizar_productos'),
    path('agregar_consulta/', views.agregar_consulta, name='agregar_consulta'),
    path('visualizar_consultas/', views.visualizar_consultas, name='visualizar_consultas'),
    path('agregar_agenda/', views.agregar_agenda, name='agregar_agenda'),
    path('agregar_mascota/<uuid:id_dueño>/', views.agregar_mascota, name='agregar_mascota'),
    path('visualizar_mascota/', views.visualizar_mascota, name='visualizar_mascota'),
    path('editar_consulta/<uuid:id_consulta>/', views.editar_consulta, name='editar_consulta'),
    path('eliminar_consulta/<uuid:id_consulta>/', views.eliminar_consulta, name='eliminar_consulta'),
    path('editar_cita/<uuid:id_agenda>/', views.editar_cita, name='editar_cita'),
    path('eliminar_cita/<uuid:id_agenda>/', views.eliminar_cita, name='eliminar_cita'),

]

handler404 = 'app.views.error_pagina_no_encontrada'
handler500 = 'app.views.error_internal_server'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)


