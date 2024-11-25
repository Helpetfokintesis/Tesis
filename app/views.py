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



from django.conf import settings
from .utils import formato_numero_chileno, enviar_mensaje_whatsapp, enviar_correo_electronico










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





    

    


#HACERLO CUANDO ESTE LA AUTENTIFICACION
#def error_prohibido(request, exception):
  #  return render(request, "403.html", status= 403)








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





def recordatorios(request):
    # Cargar todas las mascotas junto con sus recordatorios
    mascotas = Mascota.objects.prefetch_related('recordatorios').all()

    # Verificar si existe al menos un recordatorio
    hay_recordatorios = any(mascota.recordatorios.exists() for mascota in mascotas)

    # Pasar los datos al template
    data = {
        'mascota': mascotas,
        'hay_recordatorios': hay_recordatorios
    }
    return render(request, 'recepcion/recordatorios.html', data)


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





def eliminar_recordatorio(request, id_recordatorio):
    recordatorio = get_object_or_404(Recordatorio, id_recordatorio = id_recordatorio)
    recordatorio.delete()
    return redirect('recordatorios')


def marcar_completado(request, id_recordatorio):
    recordatorio = get_object_or_404(Recordatorio, id_recordatorio = id_recordatorio)
    recordatorio.estado = "Completado"
    recordatorio.save()
    return redirect('recordatorios')



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

def dashboard(request):
    return render(request, 'recepcion/dashboard.html')

def agenda(request):
    agenda = Agenda.objects.all()
    return render(request, 'recepcion/agenda.html', {'agenda': agenda})

def agregar_producto(request):
    if request.method == 'POST':
        # Obtener datos del formulario
        nombre_producto = request.POST.get('nombre_producto')
        tipo_producto = request.POST.get('tipo_producto')
        precio = request.POST.get('precio')
        stock = request.POST.get('stock')

        # Crear el producto
        Producto.objects.create(
            nombre_producto=nombre_producto,
            tipo_producto=tipo_producto,
            precio=precio,
            stock=stock
        )
        return redirect('visualizar_productos')  # Redirigir a la vista de visualización

    return render(request, 'recepcion/agregar_producto.html')

def visualizar_productos(request):
    productos = Producto.objects.all()  # Obtener todos los productos
    return render(request, 'recepcion/visualizar_productos.html', {'productos': productos})

def agregar_consulta(request):
    if request.method == 'POST':
        # Obtener datos del formulario
        mascota_id = request.POST.get('mascota')
        fecha_consulta = request.POST.get('fecha_consulta')
        motivo = request.POST.get('motivo')
        diagnostico = request.POST.get('diagnostico')
        tratamiento = request.POST.get('tratamiento')
        productos_ids = request.POST.getlist('productos')

        # Crear la consulta
        consulta = Consulta.objects.create(
            mascota=Mascota.objects.get(id=mascota_id),
            fecha_consulta=fecha_consulta,
            motivo=motivo,
            diagnostico=diagnostico,
            tratamiento=tratamiento
        )
        # Asignar productos relacionados
        consulta.productos.set(Producto.objects.filter(id_producto__in=productos_ids))

        return redirect('visualizar_consultas')  # Redirigir a la vista de visualización

    # Pasar datos al formulario
    mascotas = Mascota.objects.all()
    productos = Producto.objects.all()
    return render(request, 'recepcion/agregar_consulta.html', {'mascotas': mascotas, 'productos': productos})

def visualizar_consultas(request):
    consultas = Consulta.objects.all()
    return render(request, 'recepcion/visualizar_consultas.html', {'consultas': consultas})

def agregar_agenda(request):
    if request.method == 'POST':
        # Obtener datos del formulario
        fecha = request.POST.get('fecha')
        hora = request.POST.get('hora')
        estado = request.POST.get('estado')
        mascota_id = request.POST.get('mascota')
        usuario_id = request.POST.get('usuario')

        # Crear el registro en la agenda
        Agenda.objects.create(
            fecha=fecha,
            hora=hora,
            estado=estado,
            mascota=Mascota.objects.get(id=mascota_id),
            usuario=UsuarioSistema.objects.get(id=usuario_id)
        )
        return redirect('visualizar_agenda')  # Redirigir a la vista de visualización

    # Obtener mascotas y usuarios para los select
    mascotas = Mascota.objects.all()
    usuarios = UsuarioSistema.objects.all()
    return render(request, 'recepcion/agregar_agenda.html', {'mascotas': mascotas, 'usuarios': usuarios})

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

def visualizar_mascota(request):
    mascotas = Mascota.objects.select_related('dueño').all()
    return render(request, 'recepcion/visualizar_mascota.html', {'mascotas': mascotas})

def editar_consulta(request, id_consulta):
    consulta = get_object_or_404(Consulta, id_consulta=id_consulta)
    if request.method == 'POST':
        consulta.motivo = request.POST.get('motivo')
        consulta.diagnostico = request.POST.get('diagnostico')
        consulta.tratamiento = request.POST.get('tratamiento')
        consulta.save()
        return redirect('visualizar_consultas')
    return render(request, 'editar_consulta.html', {'consulta': consulta})

def eliminar_consulta(request, id_consulta):
    consulta = get_object_or_404(Consulta, id_consulta=id_consulta)
    consulta.delete()
    return redirect('visualizar_consultas')

def editar_cita(request, id_agenda):
    cita = get_object_or_404(Agenda, id_agenda=id_agenda)
    if request.method == 'POST':
        cita.fecha = request.POST.get('fecha')
        cita.hora = request.POST.get('hora')
        cita.estado = request.POST.get('estado')
        cita.save()
        return redirect('visualizar_agenda')
    return render(request, 'editar_cita.html', {'cita': cita})

def eliminar_cita(request, id_agenda):
    cita = get_object_or_404(Agenda, id_agenda=id_agenda)
    cita.delete()
    return redirect('visualizar_agenda')
