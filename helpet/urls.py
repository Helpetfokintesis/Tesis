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
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from two_factor.urls import urlpatterns as two_factor_urls


urlpatterns = [

    #path('admin/', admin.site.urls),
    path('', views.index, name = "index"),
    path('errores/403/', views.error_prohibido, name='error_403'),
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
    path('agregar_consulta/<uuid:id_mascota>', views.agregar_consulta, name='agregar_consulta'),
    path('visualizar_consultas/', views.visualizar_consultas, name='visualizar_consultas'),
    path('agregar_agenda/<id_mascota>/', views.agregar_agenda, name='agregar_agenda'),
    path('agregar_mascota/<uuid:id_dueño>/', views.agregar_mascota, name='agregar_mascota'),
    path('visualizar_mascota/', views.visualizar_mascota, name='visualizar_mascota'),
    path('editar_consulta/<uuid:id_consulta>/', views.editar_consulta, name='editar_consulta'),
    path('eliminar_consulta/<uuid:id_consulta>/', views.eliminar_consulta, name='eliminar_consulta'),
    path('editar_agenda/<uuid:id_agenda>/', views.editar_agenda, name='editar_agenda'),
    path('eliminar_mascota/<uuid:id_mascota>/', views.eliminar_mascota, name = "eliminar_mascota"),
    path('eliminar_cita/<uuid:id_agenda>/', views.eliminar_cita, name='eliminar_cita'),
    path('contacto/', views.contacto, name= 'contacto'),
    path('calendario/', views.calendario, name='calendario'),  # Página del calendario
    path('panel/', views.panel, name='panel'),


    path('eliminar_producto/<uuid:id_producto>/', views.eliminar_producto, name='eliminar_producto'),

    path('dashboard_usuario/', views.dashboard_usuario, name='dashboard_usuario'),
    path('perfil_usuario/', views.perfil_usuario, name='perfil_usuario'),
    path('mis_mascotas/', views.mis_mascotas, name='mis_mascotas'),
    path('editar_perfil/<uuid:id_dueño>/', views.editar_perfil, name='editar_perfil'),
    path('editar_contrasena/<uuid:id_dueño>/', views.editar_contrasena, name='editar_contrasena'),
    path('agregar_mascota/', views.agregar_mascota_dueño, name='agregar_mascota_dueño'),

    #tokens ELIMINAR DESPUES
    #path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    #path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),



    path('2fa/', include(('two_factor.urls', 'two_factor'), namespace='two_factor')),
    path('2fa/configurar/', views.configurar_2fa, name='configurar_2fa'),
    path("2fa/verificar/", views.verificar_2fa, name="verificar_2fa"),
    path("2fa/desactivar/", views.desactivar_2fa, name="desactivar_2fa"),


]

handler404 = 'app.views.error_pagina_no_encontrada'
handler500 = 'app.views.error_internal_server'
handler403 = 'app.views.error_prohibido'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

