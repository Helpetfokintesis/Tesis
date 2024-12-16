from django.db import models
from django.utils import timezone
# Create your models here.

import uuid

class Compra(models.Model):
    id_compra = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fecha_compra = models.DateField()
    total = models.DecimalField(max_digits=10, decimal_places=2)

class Dueño(models.Model):
    id_dueño = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    teléfono = models.CharField(max_length=15)
    dirección = models.CharField(max_length=255)
    correo = models.EmailField()
    ciudad = models.CharField(max_length=50)
    país = models.CharField(max_length=50)
    región = models.CharField(max_length=50)
    compras = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name="dueños", null=True, blank=True)

class Mascota(models.Model):
    id_mascota = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dueño = models.ForeignKey(Dueño, on_delete=models.CASCADE, related_name="mascotas")
    nombre = models.CharField(max_length=100)
    raza = models.CharField(max_length=50)
    especie = models.CharField(max_length=50)
    sexo = models.CharField(max_length=10)
    nacimiento = models.DateField()
    ultima_consulta = models.DateField(null=True, blank=True)

class Agenda(models.Model):
    id_agenda = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fecha = models.DateField()
    hora = models.TimeField()
    estado = models.CharField(max_length=50)
    mascota = models.ForeignKey(Mascota, on_delete=models.CASCADE)


class UsuarioSistema(models.Model):
    id_usuario = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100)
    rol = models.CharField(max_length=50)
    correo = models.EmailField(unique=True)
    contraseña_hash = models.CharField(max_length=255)



class Recordatorio(models.Model):
    id_recordatorio = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo = models.CharField(max_length=50)
    fecha = models.DateField()
    frecuencia = models.CharField(max_length=50)
    canal = models.CharField(max_length=50)
    estado = models.CharField(max_length=50)
    mascota = models.ForeignKey(Mascota, on_delete=models.CASCADE, related_name="recordatorios")


class Producto(models.Model):
    id_producto = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre_producto = models.CharField(max_length=100)
    tipo_producto = models.CharField(max_length=50)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()


class Consulta(models.Model):
    id_consulta = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mascota = models.ForeignKey(Mascota, on_delete=models.CASCADE, related_name="consultas")
    fecha_consulta = models.DateField()
    motivo = models.TextField()
    diagnóstico = models.TextField()
    tratamiento = models.TextField()
    productos = models.ManyToManyField(Producto, related_name="consultas", blank = True)


class CanalComunicacion(models.Model):
    id_canal = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo_canal = models.CharField(max_length=50)
    prioridad = models.IntegerField()



class MensajeContacto(models.Model):
    id_mensaje = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    correo = models.EmailField(verbose_name="Correo Electrónico")
    mensaje = models.TextField(verbose_name="Mensaje")
    fecha_envio = models.DateField()
    

class EnvioMensaje(models.Model):
    dueño = models.ForeignKey(Dueño, on_delete=models.CASCADE)
    fecha_envio = models.DateField()

    