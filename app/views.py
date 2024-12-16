from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseServerError, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
from app.models import Agenda, Consulta, Producto, Dueño, Mascota, UsuarioSistema,Recordatorio, MensajeContacto, EnvioMensaje
import uuid
from datetime import date
from django_otp import user_has_device
from rest_framework import viewsets
from .serializer import DueñoSerializer, MascotaSerializer

from django.contrib.auth.decorators import user_passes_test


from .utils import formato_numero_chileno, enviar_mensaje_whatsapp, enviar_correo_electronico

from datetime import datetime, timedelta
from django.contrib.auth import update_session_auth_hash
from django.db.models import Q, Prefetch
from django.db import transaction

from django_otp.plugins.otp_totp.models import TOTPDevice

import qrcode
from django.conf import settings
import os
from collections import defaultdict

# Create your views here.


class DueñoViewSet(viewsets.ModelViewSet):
    queryset  = Dueño.objects.all()
    serializer_class = DueñoSerializer





class MascotaViewSet(viewsets.ModelViewSet):
    queryset  = Mascota.objects.all()
    serializer_class = MascotaSerializer

 

#Vistas Template
def index(request):
    return render(request,'indice.html')

def error_pagina_no_encontrada(request, exception):
    return render(request, "errores/404.html", status = 404)

def error_internal_server(request):
    return HttpResponseServerError(render(request, "errores/500.html"))





    
def usuario_autentificado(user):
    return user.is_authenticated  

def es_superusuario(user):
    return user.is_superuser
    


@user_passes_test(usuario_autentificado, login_url='/errores/403/')
def configurar_2fa(request):
    user = request.user

    # Verifica si ya tiene un dispositivo configurado
    if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
        return redirect('index')  # Redirige si ya está configurado

    # Sanitiza el nombre del archivo usando el email del usuario
    email_safe = user.email.replace("@", "_at_").replace(".", "_dot_")

    devices = TOTPDevice.objects.filter(user=user, name=user.email)
    if devices.exists():
        # Si ya existen dispositivos, utiliza el primero confirmado o no
        device = devices.first()
    else:
        # Si no existen dispositivos, crea uno nuevo
        device = TOTPDevice.objects.create(user=user, name=user.email, confirmed=False)

    config_url = device.config_url

    try:
        qr = qrcode.make(config_url)
        qr_filename = f"qr_code_{email_safe}.png"  # Usa el email seguro para el nombre del archivo
        qr_path = os.path.join(settings.MEDIA_ROOT, qr_filename)
        qr.save(qr_path)

        qr_url = f"{settings.MEDIA_URL}{qr_filename}"

        if request.method == "POST":
            # Limpia mensajes existentes para evitar duplicados
            storage = messages.get_messages(request)
            storage.used = True

            token = request.POST.get("token")
            if token:
                # Verifica el token solo si el dispositivo no está confirmado
                if not device.confirmed and device.verify_token(token):
                    # Marca el dispositivo como confirmado
                    device.confirmed = True
                    device.save()

                    # Elimina el QR generado
                    if os.path.exists(qr_path):
                        os.remove(qr_path)

                    messages.success(request, "2FA activado correctamente.", extra_tags="success_2FA")
                    return redirect("index")
                else:
                    messages.error(request, "El token ingresado es inválido. Inténtalo nuevamente.", extra_tags="error_2FA")
            else:
                messages.error(request, "Debes ingresar un token para activar 2FA.", extra_tags="error_2FA")

        return render(request, "two_factor/core/setup.html", {"qr_url": qr_url, "qr_generated": True})
    except Exception as e:
        return render(request, "two_factor/core/setup.html", {"error": f"Error al configurar 2FA: {str(e)}", "qr_generated": False})




def verificar_2fa(request):
    try:
        # Obtiene el usuario temporal de la sesión
        user_id = request.session.get('temp_user_id')
        if not user_id:
            messages.error(request, "Sesión no válida. Por favor, inicia sesión nuevamente.", extra_tags="validar_2FA")
            return redirect("iniciarSesion")

        # Busca el dispositivo confirmado del usuario
        user = get_object_or_404(User, id=user_id)
        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()

        if not device:
            messages.error(request, "No tienes un dispositivo 2FA configurado.", extra_tags="validar_2FA")
            return redirect("configurar_2fa")

        if request.method == "POST":
            token = request.POST.get("token", "").strip()
            if token and device.verify_token(token):
                # Marca al usuario como verificado y lo loguea
                request.session['otp_verified'] = True
                login(request, user)
                del request.session['temp_user_id']  # Limpia el usuario temporal
                messages.success(request, "Inicio de sesión exitoso.", extra_tags="validar_2FA")
                return redirect("index")
            else:
                messages.error(request, "El token ingresado es inválido. Intenta nuevamente.", extra_tags="validar_2FA")

        return render(request, "two_factor/core/otp_required.html", {"device": device})

    except Exception as e:
        messages.error(request, f"Error al verificar 2FA: {str(e)}", extra_tags="validar_2FA")
        return redirect("index")


@user_passes_test(usuario_autentificado, login_url='/errores/403/')
def desactivar_2fa(request):
    try:
        user = request.user

        # Busca dispositivos TOTP confirmados del usuario
        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()

        if not device:
            messages.warning(request, "No tienes 2FA activo para desactivar.", extra_tags="desactivar_2FA")
            return redirect("dashboard_usuario")

        if request.method == "POST":
            # Elimina el dispositivo 2FA
            device.delete()
            messages.success(request, "2FA desactivado correctamente.", extra_tags="desactivar_2FA")
            return redirect("dashboard_usuario")

        return render(request, "two_factor/profile/disable.html")


    except Exception as e:
        messages.error(request, f"Error al desactivar 2FA: {str(e)}", extra_tags="desactivar_2FA")
        return redirect("dashboard_usuario")




def iniciarSesion(request):
    if request.method == "POST":
        correo = request.POST.get('email', '').strip()
        contraseña = request.POST.get('password', '').strip()

        # Autentica al usuario
        user = authenticate(request, username=correo, password=contraseña)
        if user:
            # Verificar si el usuario tiene 2FA configurado
            if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
                # Si no ha verificado OTP
                if not request.session.get('otp_verified', False):
                    # Almacena temporalmente el usuario para verificar el 2FA
                    request.session['temp_user_id'] = user.id
                    messages.info(request, "Por seguridad, verifica tu 2FA.")
                    return redirect('verificar_2fa')
            else:
                # Inicia sesión directamente si no tiene 2FA configurado
                login(request, user)
                messages.warning(request, "No tienes configurado 2FA. Considera activarlo para mayor seguridad.")
                return redirect('index')

        # Si las credenciales son incorrectas
        messages.error(request, "Correo o contraseña incorrectos.", extra_tags="error_inicio")
    
    return render(request, "formularioInicioUsuario.html")



#Autentificación
def error_prohibido(request, exception=None):
    return render(request, "errores/403.html", status=403)



def obtener_token_para_usuario(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }












@user_passes_test(es_superusuario, login_url='/errores/403/')
def recordatorios(request):
    # Obtener parámetros de búsqueda y filtro
    query = request.GET.get('q', '').strip()
    tipo_filtro = request.GET.get('tipo', '').strip()

    # Construir el queryset base con prefetch para optimizar relaciones
    mascotas = Mascota.objects.prefetch_related(
        Prefetch('recordatorios'),
        Prefetch('dueño')
    )

    # Aplicar filtros si existen
    if query:
        query_parts = query.split()
        mascotas = mascotas.filter(
            Q(nombre__icontains=query) |
            Q(dueño__nombre__icontains=query) |
            Q(dueño__apellidos__icontains=query) |
            (Q(dueño__nombre__icontains=query_parts[0]) & 
             Q(dueño__apellidos__icontains=query_parts[-1]) if len(query_parts) > 1 else Q())
        )

    if tipo_filtro:
        mascotas = mascotas.filter(recordatorios__tipo=tipo_filtro)

    # Clasificar las mascotas según el estado de los recordatorios
    mascotas_con_pendientes = []
    mascotas_con_completados = []
    mascotas_sin_recordatorios = []

    for mascota in mascotas:
        recordatorios = mascota.recordatorios.all()
        pendientes = [r for r in recordatorios if r.estado != 'Completado']
        completados = [r for r in recordatorios if r.estado == 'Completado']

        if pendientes:
            mascotas_con_pendientes.append({'mascota': mascota, 'recordatorios': pendientes})
        elif completados:
            mascotas_con_completados.append({'mascota': mascota, 'recordatorios': completados})
        else:
            mascotas_sin_recordatorios.append({'mascota': mascota})
    hoy = datetime.now().date()
    mañana = hoy + timedelta(days=1)
    recordatorios = Recordatorio.objects.filter(fecha__in=[hoy, mañana])
    for recordatorio in recordatorios:
    # Verificar que el estado no sea "completado"
        if recordatorio.estado != "completado":
            dueño = recordatorio.mascota.dueño

            # Comprobar si ya se envió un mensaje hoy
            if not EnvioMensaje.objects.filter(dueño=dueño, fecha_envio=hoy).exists():
                # Construir el mensaje
                mensaje = f"¡Recordatorio! \nHola {dueño.nombre} {dueño.apellidos}\nMascota: {recordatorio.mascota.nombre} \nTipo: {recordatorio.tipo} \nFecha: {recordatorio.fecha} \nEstado: {recordatorio.estado}"

                numero_telefono = dueño.teléfono
                
                if numero_telefono:
                    # Enviar el mensaje por WhatsApp
                    enviar_mensaje_whatsapp(numero_telefono, mensaje)

                    # Registrar la fecha de envío
                    EnvioMensaje.objects.create(dueño=dueño, fecha_envio=hoy)
        else:
            # Si el estado es "completado", no hacemos nada
            continue


    
    # Preparar datos para el template
    data = {
        'mascotas_pendientes': mascotas_con_pendientes,
        'mascotas_completados': mascotas_con_completados,
        'mascotas_sin_recordatorios': mascotas_sin_recordatorios,
        'query': query,
        'tipo_filtro': tipo_filtro,
    }
    return render(request, 'recepcion/recordatorios.html', data)

@user_passes_test(es_superusuario, login_url='/errores/403/')
def agregar_recordatorio(request, id_mascota):
    # Obtener la mascota o devolver un error 404
    mascota = get_object_or_404(Mascota, id_mascota=id_mascota)

    if request.method == "POST":
        # Obtener datos del formulario
        id_recordatorio = uuid.uuid4()
        tipo = request.POST.get('tipo', '').strip()
        fecha = request.POST.get('fecha', '').strip()
        frecuencia = request.POST.get('frecuencia', '').strip()
        canales = request.POST.getlist('canales_comunicacion')

        # Crear y guardar el recordatorio
        Recordatorio.objects.create(
            id_recordatorio=id_recordatorio,
            tipo=tipo,
            fecha=fecha,
            frecuencia=frecuencia,
            canal=', '.join(canales),  # Combinar canales seleccionados
            estado='Pendiente',
            mascota=mascota
        )
        return redirect('recordatorios')
    # Renderizar el formulario
    return render(request, "formularioRecordatorio.html", {'mascota': mascota})




@user_passes_test(es_superusuario, login_url='/errores/403/')
def eliminar_recordatorio(request, id_recordatorio):
    # Obtener y eliminar el recordatorio en una línea
    get_object_or_404(Recordatorio, id_recordatorio=id_recordatorio).delete()
    return redirect('recordatorios')


@user_passes_test(es_superusuario, login_url='/errores/403/')
def marcar_completado(request, id_recordatorio):
    Recordatorio.objects.filter(id_recordatorio=id_recordatorio).update(estado="Completado")
    return redirect('recordatorios')


@user_passes_test(es_superusuario, login_url='/errores/403/')
def registro(request):
    if request.method == "POST":
        try:
            with transaction.atomic():
                # Capturar datos del formulario
                correo = request.POST.get("correo_Tutor").strip()
                nombre = request.POST.get("nombre_tutor").strip()
                apellidos = request.POST.get("apellidos_Tutor").strip()
                telefono = request.POST.get("telefono_Tutor").strip()
                direccion = request.POST.get("direccion_Tutor").strip()
                ciudad = request.POST.get("ciudad_Tutor").strip()
                region = request.POST.get("region_Tutor").strip()
                nombre_mascota = request.POST.get("nombre_mascota").strip()
                raza_mascota = request.POST.get("raza_mascota").strip()
                especie_mascota = request.POST.get("especie_mascota").strip()
                sexo_mascota = request.POST.get("sexo_mascota").strip()
                fecha_nacimiento = request.POST.get("nacimiento_mascota").strip()
                pais = "Chile"

                # Verificar si el correo ya existe
                if (
                    User.objects.filter(username=correo).exists() or
                    Dueño.objects.filter(correo=correo).exists() or
                    UsuarioSistema.objects.filter(correo=correo).exists()
                ):
                    return render(request, "formularioRegistro.html", {"error": "El correo ya está registrado en el sistema."})

                # Validar y formatear número de teléfono
                telefono = formato_numero_chileno(telefono)

                # Crear instancias de Dueño y Mascota
                id_dueño = uuid.uuid4()
                id_mascota = uuid.uuid4()
                dueño = Dueño(
                    id_dueño=id_dueño,
                    nombre=nombre,
                    apellidos=apellidos,
                    teléfono=telefono,
                    dirección=direccion,
                    correo=correo,
                    ciudad=ciudad,
                    país=pais,
                    región=region
                )
                mascota = Mascota(
                    id_mascota=id_mascota,
                    dueño_id=id_dueño,
                    nombre=nombre_mascota,
                    raza=raza_mascota,
                    especie=especie_mascota,
                    sexo=sexo_mascota,
                    nacimiento=fecha_nacimiento,
                    ultima_consulta=date.today()
                )

                # Generar contraseña personalizada
                iniciales_apellido = ''.join([letra[0] for letra in apellidos.split()])
                contraseña = f"{nombre_mascota}{iniciales_apellido}{fecha_nacimiento}"

                # Crear usuario en Django
                user = User.objects.create_user(username=correo, email=correo, password=contraseña)
                user.first_name = nombre
                user.last_name = apellidos
                user.save()

                # Crear usuario en el sistema
                usuario = UsuarioSistema(
                    id_usuario=id_dueño,
                    nombre=nombre,
                    rol="AGREGAR ROLES",  # Ajustar según lógica
                    correo=correo,
                    contraseña_hash=user.password
                )

                # Guardar datos en la base de datos
                dueño.save()
                mascota.save()
                usuario.save()

                # Enviar correo y WhatsApp
                mensaje = f"Hola {nombre} {apellidos}, tu cuenta ha sido creada. Tu contraseña es: {contraseña}"
                asunto = "Cuenta creada exitosamente"
                if not enviar_correo_electronico(correo, asunto, mensaje):
                    raise Exception("No se pudo enviar el correo electrónico.")
                
                mensaje_sid = enviar_mensaje_whatsapp(telefono, mensaje)
                if not mensaje_sid:
                    return render(request, "formularioRegistro.html", {"error": "No se pudo enviar el mensaje de WhatsApp. Inténtalo nuevamente."})



                return render(request, "formularioRegistro.html", {"registro_exitoso": True})

        except Exception as e:
            return render(request, "formularioRegistro.html", {"error": f"Ha ocurrido un error: {e}"})

    # Renderizar el formulario en solicitudes GET
    return render(request, "formularioRegistro.html")



def registro_usuario(request):
    if request.method == "POST":
        try:
            # Capturar datos del formulario y eliminar espacios en blanco
            correo = request.POST.get("correo_Tutor", "").strip()
            nombre = request.POST.get("nombre_tutor", "").strip()
            apellidos = request.POST.get("apellidos_Tutor", "").strip()
            telefono = request.POST.get("telefono_Tutor", "").strip()
            direccion = request.POST.get("direccion_Tutor", "").strip()
            ciudad = request.POST.get("ciudad_Tutor", "").strip()
            region = request.POST.get("region_Tutor", "").strip()
            contraseña = request.POST.get("contraseña", "").strip()
            pais = "Chile"  # Valor constante para el país

            # Verificar si el correo ya está registrado en alguna tabla
            if (
                User.objects.filter(username=correo).exists() or
                Dueño.objects.filter(correo=correo).exists() or
                UsuarioSistema.objects.filter(correo=correo).exists()
            ):
                return render(request, "formularioRegistroUsuario.html", {"error": "El correo ya está registrado en el sistema."})

            # Validar y formatear el número de teléfono
            try:
                telefono = formato_numero_chileno(telefono)
            except ValueError as e:
                return render(request, "formularioRegistroUsuario.html", {"error": f"Teléfono inválido: {str(e)}"})

   
            with transaction.atomic():
                # Crear dueño
                id_dueño = uuid.uuid4()
                dueño = Dueño(
                    id_dueño=id_dueño,
                    nombre=nombre,
                    apellidos=apellidos,
                    telefono=telefono,
                    direccion=direccion,
                    correo=correo,
                    ciudad=ciudad,
                    pais=pais,
                    region=region
                )
                dueño.save()

                # Crear usuario del sistema Django
                user = User.objects.create_user(
                    username=correo, 
                    email=correo, 
                    password=contraseña
                )
                user.first_name = nombre
                user.last_name = apellidos
                user.save()

                # Crear usuario del sistema 
                usuario = UsuarioSistema(
                    id_usuario=id_dueño,
                    nombre=nombre,
                    rol="AGREGAR ROLES",  # Cambiar por lógica del sistema
                    correo=correo,
                    contraseña_hash=user.password 
                )
                usuario.save()

            # Devolver mensaje de éxito
            return render(request, "formularioRegistroUsuario.html", {"registro_exitoso": True})

        except Exception as e:
            return render(request, "formularioRegistroUsuario.html", {"error": f"Ha ocurrido un error: {e}"})


    return render(request, "formularioRegistroUsuario.html")


def cerrarSesion(request):
    logout(request)
    return redirect('index')


@user_passes_test(es_superusuario, login_url='/errores/403/')
def dashboard(request):
    return render(request, 'recepcion/dashboard.html')



@user_passes_test(es_superusuario, login_url='/errores/403/')

def agenda(request):
    agenda = Agenda.objects.all()
    return render(request, 'recepcion/agenda.html', {'agenda': agenda})



@user_passes_test(es_superusuario, login_url='/errores/403/')
def agregar_producto(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Capturar datos del formulario
                nombre_producto = request.POST.get('nombre_producto')
                tipo_producto = request.POST.get('tipo_producto')
                precio = request.POST.get('precio')
                stock = request.POST.get('stock')

                # Crear y guardar el producto
                Producto.objects.create(
                    id_producto=uuid.uuid4(),
                    nombre_producto=nombre_producto,
                    tipo_producto=tipo_producto,
                    precio=float(precio),  # Convertir a float para evitar problemas de tipo
                    stock=int(stock)  # Convertir a int
                )
            # Redirigir a la vista de productos
            return redirect('visualizar_productos')
        except Exception as e:
            # Manejar errores inesperados
            return render(request, 'recepcion/agregar_producto.html', {
                'error': f'Ha ocurrido un error: {e}',
            })
    return render(request, 'recepcion/agregar_producto.html')




@user_passes_test(es_superusuario, login_url='/errores/403/')
def visualizar_productos(request):
    productos = Producto.objects.all()  # Obtener todos los productos
    return render(request, 'recepcion/visualizar_productos.html', {'productos': productos})


@user_passes_test(es_superusuario, login_url='/errores/403/')
def eliminar_producto(request, id_producto):
    get_object_or_404(Producto, id_producto=id_producto).delete()
    return redirect('visualizar_productos')



def agregar_consulta(request, id_mascota):
    # Obtener la mascota o lanzar un error 404
    mascota = get_object_or_404(Mascota, id_mascota=id_mascota)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Capturar datos del formulario
                motivo = request.POST.get('motivo')
                diagnostico = request.POST.get('diagnostico')
                tratamiento = request.POST.get('tratamiento')
                productos_ids = request.POST.getlist('productos')

                # Crear la consulta
                consulta = Consulta.objects.create(
                    id_consulta=uuid.uuid4(),
                    mascota=mascota,
                    fecha_consulta=datetime.now(),
                    motivo=motivo,
                    diagnóstico=diagnostico,
                    tratamiento=tratamiento,
                )

                # Actualizar la fecha de la última consulta de la mascota
                mascota.ultima_consulta = consulta.fecha_consulta
                mascota.save()

                # Asignar productos seleccionados a la consulta
                if productos_ids:
                    productos = Producto.objects.filter(id_producto__in=productos_ids)
                    consulta.productos.set(productos)

            # Redirigir a la vista de consultas después de guardar
            return redirect('visualizar_consultas')

        except Exception as e:
            # Manejar errores inesperados
            return render(request, 'recepcion/agregar_consulta.html', {
                'mascota': mascota,
                'productos': Producto.objects.all(),
                'error': f"Ha ocurrido un error al agregar la consulta: {e}",
            })

    # Renderizar el formulario con los productos disponibles
    return render(request, 'recepcion/agregar_consulta.html', {
        'mascota': mascota,
        'productos': Producto.objects.all()
    })




@user_passes_test(es_superusuario, login_url='/errores/403/')
def visualizar_consultas(request):
    consultas = Consulta.objects.all()
    return render(request, 'recepcion/visualizar_consultas.html', {'consultas': consultas})




@user_passes_test(es_superusuario, login_url='/errores/403/')
def agregar_agenda(request, id_mascota):
    # Obtener la mascota o lanzar un error 404
    mascota = get_object_or_404(Mascota, id_mascota=id_mascota)
    if request.method == 'POST':
        try:
            # Usar una transacción para garantizar la atomicidad
            with transaction.atomic():
                # Capturar datos del formulario
                fecha = request.POST.get('fecha')
                hora = request.POST.get('hora')

                # Crear el registro en la agenda
                Agenda.objects.create(
                    fecha=fecha,
                    hora=hora,
                    estado='Pendiente',
                    mascota=mascota,
                )

            # Redirigir a la vista de la agenda después de guardar
            return redirect('agenda')

        except Exception as e:

            return render(request, 'recepcion/agregar_agenda.html', {
                'mascota': mascota,
                'error': f'Ha ocurrido un error al agregar a la agenda: {e}',
            })


    return render(request, 'recepcion/agregar_agenda.html', {'mascota': mascota})


@user_passes_test(es_superusuario, login_url='/errores/403/')
def agregar_mascota(request, id_dueño):
    # Obtener el dueño o lanzar un error 404 si no existe
    dueño = get_object_or_404(Dueño, id_dueño=id_dueño)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Capturar datos del formulario
                nombre = request.POST.get('nombre').strip()
                raza = request.POST.get('raza').strip()
                especie = request.POST.get('especie').strip()
                sexo = request.POST.get('sexo').strip()
                nacimiento = request.POST.get('nacimiento').strip()

                # Crear nueva mascota asociada al dueño
                Mascota.objects.create(
                    id_mascota=uuid.uuid4(),  # Generar UUID único
                    dueño=dueño,
                    nombre=nombre,
                    raza=raza,
                    especie=especie,
                    sexo=sexo,
                    nacimiento=nacimiento
                )

            # Redirigir a la vista de mascotas después de guardar
            return redirect('visualizar_mascota')

        except Exception as e:
            # Manejar errores y mostrar mensaje al usuario
            return render(request, 'recepcion/agregar_mascota.html', {
                'dueño': dueño,
                'error': f"Ha ocurrido un error al agregar la mascota: {e}"
            })
    # Renderizar el formulario en solicitudes GET
    return render(request, 'recepcion/agregar_mascota.html', {'dueño': dueño})

def visualizar_mascota(request):
    # Obtén el término de búsqueda desde el formulario
    query = request.GET.get('q', '').strip()

    # Consulta todas las mascotas y sus dueños
    mascotas = Mascota.objects.select_related('dueño').all()

    if query:
        # Dividir la consulta en palabras separadas
        query_parts = query.split()

        if len(query_parts) == 1:
            # Si solo hay una palabra, buscar en nombre o apellidos
            mascotas = mascotas.filter(
                Q(dueño__nombre__icontains=query) |
                Q(dueño__apellidos__icontains=query) |
                Q(nombre__icontains=query)  # Nombre de la mascota
            )
        elif len(query_parts) == 2:
            # Si hay dos palabras, buscar nombre y primer apellido
            mascotas = mascotas.filter(
                Q(dueño__nombre__icontains=query_parts[0], dueño__apellidos__icontains=query_parts[1]) |
                Q(nombre__icontains=query)  # También buscar por nombre de mascota completo
            )
        else:
            # Si hay tres o más palabras, buscar nombre, primer apellido y segundo apellido
            mascotas = mascotas.filter(
                Q(dueño__nombre__icontains=query_parts[0], dueño__apellidos__icontains=" ".join(query_parts[1:])) |
                Q(nombre__icontains=query)  # También buscar por nombre de mascota completo
            )

    # Agrupa las mascotas por dueño
    dueños_mascotas = {}
    for mascota in mascotas:
        if mascota.dueño not in dueños_mascotas:
            dueños_mascotas[mascota.dueño] = []
        dueños_mascotas[mascota.dueño].append(mascota)

    context = {
        'dueños_mascotas': dueños_mascotas,
        'query': query,  # Incluye el término de búsqueda para mantenerlo en el formulario
    }
    return render(request, 'recepcion/visualizar_mascota.html', context)




@user_passes_test(es_superusuario, login_url='/errores/403/')
def eliminar_mascota(request, id_mascota):
    get_object_or_404(Mascota, id_mascota = id_mascota).delete()
    return redirect('visualizar_mascota')







@user_passes_test(es_superusuario, login_url='/errores/403/')
def editar_consulta(request, id_consulta):
    return render(request, 'tutor/editar_consulta.html')




#ARREGLAR
@user_passes_test(es_superusuario, login_url='/errores/403/')
def editar_agenda(request, id_agenda):
    return render(request, 'recepcion/editar_cita.html')


@user_passes_test(es_superusuario, login_url='/errores/403/')
def eliminar_consulta(request, id_consulta):
    get_object_or_404(Consulta, id_consulta=id_consulta).delete()
    return redirect('visualizar_consultas')


@user_passes_test(es_superusuario, login_url='/errores/403/')
def eliminar_cita(request, id_agenda):
    get_object_or_404(Agenda, id_agenda=id_agenda).delete()
    return redirect('agenda')









@user_passes_test(usuario_autentificado, login_url='/errores/403/')
def dashboard_usuario(request):
    user = request.user
    tiene_2fa = TOTPDevice.objects.filter(user=user, confirmed=True).exists()
    return render(request, 'tutor/dashboard_usuario.html', {'tiene_2fa': tiene_2fa})


@user_passes_test(usuario_autentificado, login_url='/errores/403/')
def perfil_usuario(request):
  
    usuario = get_object_or_404(Dueño, correo = request.user.email)  # Obtiene al usuario autenticado
    return render(request, 'tutor/perfil_usuario.html', {'usuario': usuario})


@user_passes_test(usuario_autentificado, login_url='/errores/403/')
def mis_mascotas(request):
    usuario = get_object_or_404(Dueño, correo=request.user.email)  # Obtiene al usuario autenticado
    mascotas = Mascota.objects.filter(dueño=usuario).prefetch_related('recordatorios')  # Carga las mascotas y sus recordatorios

    # Filtrar recordatorios pendientes para cada mascota
    mascotas_con_recordatorios = []
    for mascota in mascotas:
        recordatorios_pendientes = mascota.recordatorios.exclude(estado="Completado")
        mascotas_con_recordatorios.append({
            'mascota': mascota,
            'recordatorios': recordatorios_pendientes
        })
    
    return render(request, 'tutor/mis_mascotas.html', {'mascotas': mascotas_con_recordatorios})


@user_passes_test(usuario_autentificado, login_url='/errores/403/')
def editar_perfil(request, id_dueño):
    usuario = get_object_or_404(Dueño, id_dueño=id_dueño)

    if request.method == 'POST':
        # Recuperar los datos enviados desde el formulario
        nombre = request.POST.get('nombre')
        apellidos = request.POST.get('apellidos')
        telefono = request.POST.get('telefono')
        correo = request.POST.get('correo')
        direccion = request.POST.get('direccion')
        ciudad = request.POST.get('ciudad')
        region = request.POST.get('region')
        pais = request.POST.get('pais')

        # Validar campos obligatorios
        if not nombre or not correo:
            messages.error(request, 'Los campos "Nombre" y "Correo" son obligatorios.')
            return redirect('editar_perfil', id_dueño=id_dueño)

        # Actualizar los campos del modelo Dueño
        usuario.nombre = nombre
        usuario.apellidos = apellidos
        usuario.teléfono = telefono
        usuario.correo = correo
        usuario.dirección = direccion
        usuario.ciudad = ciudad
        usuario.región = region
        usuario.país = pais

        usuario.save()

        # Actualizar el modelo UsuarioSistema
        usuario_sistema = get_object_or_404(UsuarioSistema, correo=request.user.email)
        usuario_sistema.correo = correo
        usuario_sistema.save()

        # Actualizar el modelo User de Django
        user_django = get_object_or_404(User, email=request.user.email)
        user_django.username = correo
        user_django.email = correo
        user_django.save()

        # Mostrar un mensaje de éxito
        messages.success(request, 'Tu perfil ha sido actualizado correctamente.')
        return redirect('perfil_usuario')

    return render(request, 'tutor/editar_perfil.html', {'usuario': usuario})


@user_passes_test(usuario_autentificado, login_url='/errores/403/')
def editar_contrasena(request, id_dueño):
    # Obtener el usuario actual
    dueño = get_object_or_404(Dueño, id_dueño=id_dueño)
    usuario_sistema = get_object_or_404(UsuarioSistema, correo=dueño.correo)
    user = get_object_or_404(User, username=dueño.correo)

    if request.method == 'POST':
        contrasena_actual = request.POST.get('contrasena_actual')
        nueva_contrasena = request.POST.get('nueva_contrasena')
        confirmar_contrasena = request.POST.get('confirmar_contrasena')

        # Validar que las contraseñas coinciden
        if nueva_contrasena != confirmar_contrasena:
            messages.error(request, 'La nueva contraseña y su confirmación no coinciden.')
            return redirect('editar_contrasena', id_dueño=id_dueño)

        # Verificar la contraseña actual en el modelo `User`
        if not user.check_password(contrasena_actual):
            messages.error(request, 'La contraseña actual es incorrecta.')
            return redirect('editar_contrasena', id_dueño=id_dueño)

        # Actualizar la contraseña en el modelo `User`
        user.set_password(nueva_contrasena)
        user.save()

        # Guardar la contraseña hasheada en el modelo `UsuarioSistema`
        usuario_sistema.contraseña_hash = user.password  # Copia el hash de la contraseña del modelo `User`
        usuario_sistema.save()

        # Mantener la sesión activa después de cambiar la contraseña
        update_session_auth_hash(request, user)

        # Mensaje de éxito y redirección
        messages.success(request, 'Tu contraseña ha sido actualizada correctamente.')
        return redirect('perfil_usuario')  # Ajusta según la página de perfil

    return render(request, 'tutor/editar_contrasena.html', {'usuario': user})



@user_passes_test(usuario_autentificado, login_url='/errores/403/')
def agregar_mascota_dueño(request):
    dueño = get_object_or_404(Dueño, correo = request.user.email)
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        raza = request.POST.get('raza', '')
        especie = request.POST.get('especie')
        sexo = request.POST.get('sexo')
        nacimiento = request.POST.get('nacimiento')

        # Crear la nueva mascota asociada al usuario actual
        mascota = Mascota(
            dueño=dueño,    
            nombre=nombre,
            raza=raza,
            especie=especie,
            sexo=sexo,
            nacimiento=nacimiento,
        )
        mascota.save()
        messages.success(request, 'Mascota registrada con éxito.')
        return redirect('dashboard_usuario')  # Redirige al dashboard del usuario

    return render(request, 'tutor/agregar_mascota2.html')  # Muestra el formulario



def contacto(request):
    if request.method == "POST":
        id_mensaje = uuid.uuid4()
        nombre = request.POST.get("nombre")
        correo = request.POST.get("correo")
        mensaje = request.POST.get("mensaje")
        contacto = MensajeContacto(
            id_mensaje,
            nombre,
            correo, 
            mensaje,
            fecha_envio=datetime.now().date()
        )
        contacto.save(
        )
        return redirect("index")
    return render(request, 'contacto.html')




def calendario(request):
    return render(request, 'recepcion/calendario.html')

from datetime import date

def panel(request):
    tutores = Dueño.objects.all()
    mascotas = Mascota.objects.all()
    recordatorios = Recordatorio.objects.all()

    contador_mascota = mascotas.count()
    contador_recordatorio = recordatorios.count()
    contador_tutores = tutores.count()

    # Para cada mascota, obtener sus recordatorios y calcular los días restantes
    mascotas_con_recordatorios = []
    for mascota in mascotas:
        recordatorios_mascota = mascota.recordatorios.all()  # Obtener todos los recordatorios de esta mascota
        recordatorios_info = []
        
        for recordatorio in recordatorios_mascota:
            # Calcular la diferencia de días entre la fecha actual y la fecha del recordatorio
            diferencia_dias = (recordatorio.fecha - date.today()).days
            recordatorios_info.append({
                'tipo': recordatorio.tipo,
                'fecha': recordatorio.fecha,
                'diferencia_dias': diferencia_dias
            })
        
        if recordatorios_info:
            mascotas_con_recordatorios.append({
                'mascota': mascota,
                'recordatorios': recordatorios_info
            })

    data = {
        'mascotas': mascotas,
        'contador_mascota': contador_mascota,
        'contador_recordatorio': contador_recordatorio,
        'contador_tutores': contador_tutores,
        'mascotas_con_recordatorios': mascotas_con_recordatorios
    }

    return render(request, 'recepcion/panel.html', data)

