from rest_framework import serializers
from .models import Dueño, Mascota

class   DueñoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dueño
        fields = '__all__'

class   MascotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mascota
        fields = '__all__'