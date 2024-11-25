
from django.urls import path, include
from rest_framework import routers
from app import views


router = routers.DefaultRouter()
router.register(r'dueño', views.DueñoViewSet)

router.register(r'mascota', views.MascotaViewSet)

urlpatterns = [
    path('', include(router.urls))
]