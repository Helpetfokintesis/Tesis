from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseServerError
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User

from app.models import Agenda, Consulta, Producto, Dueño, Mascota, UsuarioSistema,Recordatorio
import uuid
from datetime import date

from rest_framework import viewsets
from .serializer import DueñoSerializer, MascotaSerializer

from django.contrib.auth.decorators import user_passes_test

from django.conf import settings
from .utils import formato_numero_chileno, enviar_mensaje_whatsapp, enviar_correo_electronico

from datetime import datetime

from django.db.models import Q







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
    


#HACERLO CUANDO ESTE LA AUTENTIFICACION
def error_prohibido(request, exception=None):
    return render(request, "errores/403.html", status=403)








#Autentificación
def iniciarSesion(request):
    if request.method == "POST":
        correo = request.POST.get('email')
        contraseña = request.POST.get('password')

        # Autenticar usando el correo como username
        user = authenticate(request, username=correo, password=contraseña)

        if user is not None:
            login(request, user)
            return redirect('index')  # Redirigir al índice
        else:
            messages.error(request, "Correo o contraseña incorrectos.")  # Mensaje de error
    return render(request, "formularioInicioUsuario.html")




@user_passes_test(es_superusuario, login_url='/errores/403/')
def recordatorios(request):
    # Obtener parámetros de búsqueda y filtro
    query = request.GET.get('q', '').strip()  # Búsqueda por nombre
    tipo_filtro = request.GET.get('tipo', '').strip()  # Filtro por tipo de recordatorio

    # Cargar todas las mascotas
    mascotas = Mascota.objects.prefetch_related('recordatorios', 'dueño').all()

    # Aplicar filtros si hay búsqueda o tipo seleccionado
    if query:
        mascotas = mascotas.filter(
            Q(nombre__icontains=query) |  # Buscar por nombre de la mascota
            Q(dueño__nombre__icontains=query) |  # Buscar por nombre del dueño
            Q(dueño__apellidos__icontains=query) |  # Buscar por apellido del dueño
            Q(dueño__nombre__icontains=query.split()[0], dueño__apellidos__icontains=query.split()[-1])  # Nombre y apellido
        )

    if tipo_filtro:
        mascotas = mascotas.filter(recordatorios__tipo=tipo_filtro)

    # Separar las mascotas en grupos según el estado de los recordatorios
    mascotas_con_pendientes = []
    mascotas_con_completados = []
    mascotas_sin_recordatorios = []

    for mascota in mascotas:
        completados = mascota.recordatorios.filter(estado='Completado')
        pendientes = mascota.recordatorios.exclude(estado='Completado')

        if pendientes.exists():
            mascotas_con_pendientes.append({'mascota': mascota, 'recordatorios': pendientes})
        elif completados.exists():
            mascotas_con_completados.append({'mascota': mascota, 'recordatorios': completados})
        else:
            mascotas_sin_recordatorios.append({'mascota': mascota})

    # Pasar los datos al template
    data = {
        'mascotas_pendientes': mascotas_con_pendientes,
        'mascotas_completados': mascotas_con_completados,
        'mascotas_sin_recordatorios': mascotas_sin_recordatorios,
        'query': query,  # Para mostrar el texto en el campo de búsqueda
        'tipo_filtro': tipo_filtro,  # Para mantener el filtro seleccionado
    }
    return render(request, 'recepcion/recordatorios.html', data)

@user_passes_test(es_superusuario, login_url='/errores/403/')
def agregar_recordatorio(request, id_mascota):
    mascota = get_object_or_404(Mascota, id_mascota = id_mascota)

    if request.method == "POST":

        id_recordatorio = uuid.uuid4()
        tipo = request.POST.get('tipo')
        fecha = request.POST.get("fecha")
        frecuencia = request.POST.get('frecuencia')
        canales = request.POST.getlist('canales_comunicacion')
        recordatorio = Recordatorio(
            id_recordatorio=id_recordatorio,
            tipo=tipo,
            fecha=fecha,
            frecuencia=frecuencia,
            canal=', '.join(canales),  # Unir canales en una sola cadena si son
            estado='Pendiente',
            mascota=mascota
        )
        recordatorio.save()
        return redirect('recordatorios')
    return render(request, "formularioRecordatorio.html", {'mascota':mascota})




@user_passes_test(es_superusuario, login_url='/errores/403/')
def eliminar_recordatorio(request, id_recordatorio):
    recordatorio = get_object_or_404(Recordatorio, id_recordatorio = id_recordatorio)
    recordatorio.delete()
    return redirect('recordatorios')




@user_passes_test(es_superusuario, login_url='/errores/403/')
def marcar_completado(request, id_recordatorio):
    recordatorio = get_object_or_404(Recordatorio, id_recordatorio = id_recordatorio)
    recordatorio.estado = "Completado"
    recordatorio.save()
    return redirect('recordatorios')


@user_passes_test(es_superusuario, login_url='/errores/403/')
def registro(request):
    try:
        if request.method == "POST":
            correo = request.POST.get("correo_Tutor")

            # Verificar si el correo ya existe en alguna de las tablas
            if (
                User.objects.filter(username=correo).exists() or
                Dueño.objects.filter(correo=correo).exists() or
                UsuarioSistema.objects.filter(correo=correo).exists()
            ):
                return render(request, "formularioRegistro.html", {"error": "El correo ya está registrado en el sistema."})
            #CREACION DUEÑO
            id_dueño = uuid.uuid4()
            nombre = request.POST.get("nombre_tutor")
            apellidos = request.POST.get("apellidos_Tutor")
            telefono = request.POST.get("telefono_Tutor")
            direccion = request.POST.get("direccion_Tutor")
            ciudad = request.POST.get("ciudad_Tutor")
            pais = "Chile"
            region = request.POST.get("region_Tutor")

            # Ajusta el número al formato chileno si es necesario
            try:
                telefono = formato_numero_chileno(telefono)
            except ValueError as e:
                return render(request, "formularioRegistro.html", {"error": str(e)})
            

        
        
            #CREACION MASCOTA
            id_mascota = uuid.uuid4()
            nombre_mascota = request.POST.get("nombre_mascota")
            raza_mascota = request.POST.get("raza_mascota")
            especie_mascota = request.POST.get("especie_mascota")
            sexo_mascota = request.POST.get("sexo_mascota")
            fecha_nacimiento = request.POST.get("nacimiento_mascota")
            ultima_consulta = date.today()


            #GUARDANDO DATOS
            dueño = Dueño(id_dueño, nombre, apellidos, telefono, direccion, correo, ciudad, pais, region)

            mascota = Mascota(id_mascota, id_dueño, nombre_mascota, raza_mascota, especie_mascota, sexo_mascota, fecha_nacimiento, ultima_consulta)
            
            



            # Generar contraseña personalizada
            iniciales_apellido = ''.join([letra[0] for letra in apellidos.split()])
            contraseña = f"{nombre_mascota}{iniciales_apellido}{fecha_nacimiento}"






            #mensaje = f"Hola {nombre}, tu cuenta ha sido creada. Tu contraseña es: {contraseña}"

            # Enviar mensaje de WhatsApp al número capturado
            #mensaje_sid = enviar_mensaje_whatsapp(telefono, mensaje)
            #if not mensaje_sid:
            #   return render(request, "formularioRegistro.html", {"error": "No se pudo enviar el mensaje de WhatsApp. Inténtalo nuevamente."})



            mensaje = f"hola {nombre} {apellidos}, tú cuenta ha sido creada. Tú contraseña es: {contraseña}"
            asunto = "Cuenta creada exitosamente"

            correo_enviado = enviar_correo_electronico(correo, asunto, mensaje)
            if not correo_enviado:
                return render(request, "formularioRegistro.html", {"error": "No se pudo enviar el correo electrónico. Inténtalo nuevamente."})





            #CREANDO USUARIO SISTEMA DJANGO
            user = User.objects.create_user(correo, correo, contraseña)
            user.first_name = nombre
            user.last_name = apellidos
            



            #CREANDO USUARIO SISTEMA 
            id_usuarioSis = id_dueño
            nombre_usuarioSis =  nombre
            rol_usuarioSis = "AGREGAR ROLES"
            correo_usuarioSis = correo
            contraseña_hash = user.password


            usuario = UsuarioSistema(id_usuarioSis, nombre_usuarioSis, rol_usuarioSis, correo_usuarioSis, contraseña_hash)


            dueño.save()
            mascota.save()    
            user.save()
            usuario.save()

            
            return render(request, "formularioRegistro.html", {"registro_exitoso": True})

    except Exception as e:
        return render(request, "formularioRegistro.html", {"error": f"Ha ocurrido un error: {e}"})
    return render(request,"formularioRegistro.html")




def registro_usuario(request):
    try:
        if request.method == "POST":
            correo = request.POST.get("correo_Tutor")

            # Verificar si el correo ya existe en alguna de las tablas
            if (
                User.objects.filter(username=correo).exists() or
                Dueño.objects.filter(correo=correo).exists() or
                UsuarioSistema.objects.filter(correo=correo).exists()
            ):
                return render(request, "formularioRegistro.html", {"error": "El correo ya está registrado en el sistema."})
            #CREACION DUEÑO
            id_dueño = uuid.uuid4()
            nombre = request.POST.get("nombre_tutor")
            apellidos = request.POST.get("apellidos_Tutor")
            telefono = request.POST.get("telefono_Tutor")
            direccion = request.POST.get("direccion_Tutor")
            ciudad = request.POST.get("ciudad_Tutor")
            pais = "Chile"
            region = request.POST.get("region_Tutor")
            contraseña = request.POST.get("contraseña")

            # Ajusta el número al formato chileno si es necesario
            try:
                telefono = formato_numero_chileno(telefono)
            except ValueError as e:
                return render(request, "formularioRegistro.html", {"error": str(e)})
            

            dueño = Dueño(id_dueño, nombre, apellidos, telefono, direccion, correo, ciudad, pais, region)


            #CREANDO USUARIO SISTEMA DJANGO
            user = User.objects.create_user(correo, correo, contraseña)
            user.first_name = nombre
            user.last_name = apellidos
            

            #CREANDO USUARIO SISTEMA 
            id_usuarioSis = id_dueño
            nombre_usuarioSis =  nombre
            rol_usuarioSis = "AGREGAR ROLES"
            correo_usuarioSis = correo
            contraseña_hash = user.password


            usuario = UsuarioSistema(id_usuarioSis, nombre_usuarioSis, rol_usuarioSis, correo_usuarioSis, contraseña_hash)


            dueño.save()
            user.save()
            usuario.save()

            
            return render(request, "formularioRegistroUsuario.html", {"registro_exitoso": True})

    except Exception as e:
        return render(request, "formularioRegistroUsuario.html", {"error": f"Ha ocurrido un error: {e}"})
    return render(request,"formularioRegistroUsuario.html")

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
        # Obtener datos del formulario
        nombre_producto = request.POST.get('nombre_producto')
        tipo_producto = request.POST.get('tipo_producto')
        precio = request.POST.get('precio')
        stock = request.POST.get('stock')

        # Crear el producto
        producto = Producto(
            id_producto = uuid.uuid4(),
            nombre_producto = nombre_producto,
            tipo_producto = tipo_producto,
            precio = precio,
            stock = stock
        )
        producto.save()
        return redirect('visualizar_productos')  # Redirigir a la vista de visualización

    return render(request, 'recepcion/agregar_producto.html')

@user_passes_test(es_superusuario, login_url='/errores/403/')
def visualizar_productos(request):
    productos = Producto.objects.all()  # Obtener todos los productos
    return render(request, 'recepcion/visualizar_productos.html', {'productos': productos})

def eliminar_producto(request, id_producto):
    producto = get_object_or_404(Producto, id_producto=id_producto)
    producto.delete()
    return redirect('visualizar_productos')



@user_passes_test(es_superusuario, login_url='/errores/403/')
def agregar_consulta(request, id_mascota):
    mascota = get_object_or_404(Mascota, id_mascota=id_mascota)  # Obtener la mascota por ID
    if request.method == 'POST':
        # Obtener datos del formulario
        motivo = request.POST.get('motivo')
        diagnostico = request.POST.get('diagnostico')
        tratamiento = request.POST.get('tratamiento')
        productos_ids = request.POST.getlist('productos')  # Obtener lista de IDs de productos seleccionados

        # Crear la consulta (sin asignar productos todavía)
        consulta = Consulta.objects.create(
            id_consulta=uuid.uuid4(),
            mascota=mascota,
            fecha_consulta=datetime.now(),
            motivo=motivo,
            diagnóstico=diagnostico,
            tratamiento=tratamiento,
        )

        # Asignar productos seleccionados a la consulta
        if productos_ids:  # Verifica si hay productos seleccionados
            productos = Producto.objects.filter(id_producto__in=productos_ids)  # Filtra los productos seleccionados
            consulta.productos.set(productos)  # Asigna los productos seleccionados a la consulta

        return redirect('visualizar_consultas')  # Redirigir a la vista de visualización

    # Pasar datos al formulario
    productos = Producto.objects.all()  # Obtener todos los productos disponibles
    return render(
        request,
        'recepcion/agregar_consulta.html',
        {'mascota': mascota, 'productos': productos}
    )


@user_passes_test(es_superusuario, login_url='/errores/403/')
def visualizar_consultas(request):
    consultas = Consulta.objects.all()
    return render(request, 'recepcion/visualizar_consultas.html', {'consultas': consultas})

@user_passes_test(es_superusuario, login_url='/errores/403/')

def agregar_agenda(request, id_mascota):
    mascota = get_object_or_404(Mascota, id_mascota = id_mascota)
  
    if request.method == 'POST':
        # Obtener datos del formulario
        fecha = request.POST.get('fecha')
        hora = request.POST.get('hora')

        # Crear el registro en la agenda
        Agenda.objects.create(
            fecha=fecha,
            hora=hora,
            estado='Pendiente',
            mascota= mascota,
        )
        return redirect('agenda')  # Redirigir a la vista de visualización

    return render(request, 'recepcion/agregar_agenda.html', {'mascota': mascota})

@user_passes_test(es_superusuario, login_url='/errores/403/')
def agregar_mascota(request, id_dueño):
    dueño = get_object_or_404(Dueño, id_dueño=id_dueño)  # Obtiene el dueño por ID
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        raza = request.POST.get('raza')
        especie = request.POST.get('especie')
        sexo = request.POST.get('sexo')
        nacimiento = request.POST.get('nacimiento')

        # Crear nueva mascota asociada al dueño
        mascota = Mascota(
            id_mascota=uuid.uuid4(),  # Generar UUID único
            dueño=dueño,  # Pasar el objeto Dueño directamente
            nombre=nombre,
            raza=raza,
            especie=especie,
            sexo=sexo,
            nacimiento=nacimiento
        )
        mascota.save()  # Guardar la mascota en la base de datos
        return redirect('visualizar_mascota')  # Redirigir a la lista de mascotas

    # Renderizar el formulario para agregar la mascota
    return render(request, 'recepcion/agregar_mascota.html', {'dueño': dueño})

@user_passes_test(es_superusuario, login_url='/errores/403/')
def visualizar_mascota(request):
    mascotas = Mascota.objects.select_related('dueño').all()
    return render(request, 'recepcion/visualizar_mascota.html', {'mascotas': mascotas})

@user_passes_test(es_superusuario, login_url='/errores/403/')
def editar_consulta(request, id_consulta):
    consulta = get_object_or_404(Consulta, id_consulta=id_consulta)
    if request.method == 'POST':
        consulta.motivo = request.POST.get('motivo')
        consulta.diagnostico = request.POST.get('diagnostico')
        consulta.tratamiento = request.POST.get('tratamiento')
        consulta.save()
        return redirect('visualizar_consultas')
    return render(request, 'tutor/editar_consulta.html', {'consulta': consulta})

@user_passes_test(es_superusuario, login_url='/errores/403/')
def eliminar_consulta(request, id_consulta):
    consulta = get_object_or_404(Consulta, id_consulta=id_consulta)
    consulta.delete()
    return redirect('visualizar_consultas')

@user_passes_test(es_superusuario, login_url='/errores/403/')
def editar_cita(request, id_agenda):
    cita = get_object_or_404(Agenda, id_agenda=id_agenda)
    if request.method == 'POST':
        cita.fecha = request.POST.get('fecha')
        cita.hora = request.POST.get('hora')
        cita.estado = request.POST.get('estado')
        cita.save()
        return redirect('agenda')
    return render(request, 'editar_cita.html', {'cita': cita})

@user_passes_test(es_superusuario, login_url='/errores/403/')

def eliminar_cita(request, id_agenda):
    cita = get_object_or_404(Agenda, id_agenda=id_agenda)
    cita.delete()
    return redirect('agenda')










def dashboard_usuario(request):
    return render(request, 'tutor/dashboard_usuario.html')

def perfil_usuario(request):
    """Renderiza el perfil del usuario."""
    usuario = get_object_or_404(Dueño, correo = request.user.email)  # Obtiene al usuario autenticado
    return render(request, 'tutor/perfil_usuario.html', {'usuario': usuario})

def mis_mascotas(request):
    """Renderiza el listado de mascotas del usuario."""
    usuario = get_object_or_404(Dueño, correo = request.user.email)  # Obtiene al usuario autenticado
    mascotas = Mascota.objects.filter(dueño=usuario)  # Filtra las mascotas por dueño
    return render(request, 'tutor/mis_mascotas.html', {'mascotas': mascotas})

def editar_perfil(request, id_dueño):
    # Obtener el usuario actual
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
        
        # Actualizar los campos del usuario
        usuario.nombre = nombre
        usuario.apellidos = apellidos
        usuario.teléfono = telefono
        usuario.correo = correo
        usuario.dirección = direccion
        usuario.ciudad = ciudad
        usuario.región = region
        usuario.país = pais
        usuario.save()  # Guardar los cambios en la base de datos

        # Mostrar un mensaje de éxito
        messages.success(request, 'Tu perfil ha sido actualizado correctamente.')
        return redirect('perfil_usuario')  # Redirige a la página del perfil (ajusta según corresponda)

    # Renderizar el formulario con los datos actuales del usuario
    return render(request, 'tutor/editar_perfil.html', {'usuario': usuario})

def editar_contrasena(request):
    # Obtener el usuario actual
    dueño = get_object_or_404(Dueño, correo = request.user.email)
    usuario = get_object_or_404(UsuarioSistema, correo = request.user.email)
    user = get_object_or_404(User, username = request.user.email)
    if request.method == 'POST':
        contrasena_actual = request.POST.get('contrasena_actual')
        nueva_contrasena = request.POST.get('nueva_contrasena')
        confirmar_contrasena = request.POST.get('confirmar_contrasena')

        # Validar que las contraseñas coinciden
        if nueva_contrasena != confirmar_contrasena:
            messages.error(request, 'La nueva contraseña y su confirmación no coinciden.')
            return redirect('editar_contrasena')

        # Verificar la contraseña actual
        usuario = request.user
        if not usuario.check_password(contrasena_actual):
            messages.error(request, 'La contraseña actual es incorrecta.')
            return redirect('editar_contrasena')

        # Actualizar la contraseña
        usuario.set_password(nueva_contrasena)
        usuario.save()

        # Mantener la sesión activa después de cambiar la contraseña
        update_session_auth_hash(request, usuario)

        # Mensaje de éxito y redirección
        messages.success(request, 'Tu contraseña ha sido actualizada correctamente.')
        return redirect('perfil')  # Ajusta según la página de perfil

    return render(request, 'tutor/editar_contrasena.html', {'usuario': usuario})

def agregar_mascota_dueno(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        raza = request.POST.get('raza', '')
        especie = request.POST.get('especie')
        sexo = request.POST.get('sexo')
        nacimiento = request.POST.get('nacimiento')

        # Crear la nueva mascota asociada al usuario actual
        mascota = Mascota(
            dueño=request.user,  # Se asocia la mascota al usuario autenticado
            nombre=nombre,
            raza=raza,
            especie=especie,
            sexo=sexo,
            nacimiento=nacimiento,
        )
        mascota.save()
        messages.success(request, 'Mascota registrada con éxito.')
        return redirect('dashboard_usuario')  # Redirige al dashboard del usuario

    return render(request, 'agregar_mascota.html')  # Muestra el formulario