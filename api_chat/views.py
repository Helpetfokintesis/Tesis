import os
from dotenv import load_dotenv
from openai import OpenAI
from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings
from app.models import UsuarioSistema, Mascota, Recordatorio, Consulta, Dueño
from datetime import datetime
import json
from .utils import generate_access_token
from datetime import datetime, timedelta

# Clave secreta para firmar los tokens
SECRET_KEY = settings.SECRET_KEY

load_dotenv()
client = OpenAI(api_key = os.getenv('OPENAI_API_KEY'))  

@csrf_exempt
def verify_email(request):
    """
    Vista separada para verificar el correo.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            email = data.get("email")

            if not email:
                return JsonResponse(
                    {"error": "No se proporcionó el correo electrónico."},
                    status=400
                )
            
            # Buscar el usuario en la base de datos
            user = UsuarioSistema.objects.filter(correo=email).first()

            if user:
                return JsonResponse({
                    "status": "verified",
                    "message": f"¡Hola {user.nombre}! ¿En qué puedo ayudarte?",
                    "options": [
                        "1. Gestionar recordatorios",
                        "2. Obtener recomendaciones/cuidados",
                        "3. Derivar consulta médica"
                    ]
                }, status=200)
            else:
                return JsonResponse({
                    "status": "not_found",
                    "message": "El correo no está registrado. ¿Deseas registrarte?"
                }, status=404)

        except json.JSONDecodeError:
            return JsonResponse(
                {"error": "El cuerpo de la solicitud debe ser JSON válido."},
                status=400
            )
        except Exception as e:
            return JsonResponse(
                {"error": f"Error interno: {str(e)}"},
                status=500
            )

    return JsonResponse({"error": "Método no permitido."}, status=405)

@csrf_exempt
def chatbot_interaccion(request):
    """
    Maneja la interacción del chatbot con validación del correo y estado persistente.
    """
    if request.method == "POST":
        try:
            # Parsear datos del cuerpo
            data = json.loads(request.body)
            mensaje = data.get("message", "").strip()

            if not mensaje:
                return JsonResponse({"error": "El mensaje no puede estar vacío."}, status=400)

            # Obtener estado y correo de la sesión
            estado = request.session.get("estado", "validar_correo")
            email = request.session.get("email", None)

            # **Comando de Salida**: Verificar si el usuario desea salir
            if mensaje.lower() in ["salir", "exit", "cerrar"]:
                request.session.flush()  # Reiniciar la sesión
                return JsonResponse({
                    "message": "La sesión se ha reiniciado. Por favor, escribe tu correo electrónico para comenzar.",
                    "state": "validar_correo",
                    "email": None
                }, status=200)

            # **CASO 1:** Validar correo electrónico
            if estado == "validar_correo":
                dueño = Dueño.objects.filter(correo=mensaje).first()
                if dueño:
                    # Guardar estado y correo en la sesión
                    request.session["estado"] = "procesar_intencion"
                    request.session["email"] = dueño.correo
                    return JsonResponse({
                        "status": "verified",
                        "message": f"¡Hola {dueño.nombre}! ¿En qué puedo ayudarte?",
                        "options": [
                            "1. Gestionar recordatorios",
                            "2. Obtener recomendaciones/cuidados",
                            "3. Derivar consulta médica"
                        ],
                        "state": "procesar_intencion",
                        "email": dueño.correo
                    }, status=200)
                else:
                    return JsonResponse({
                        "status": "not_verified",
                        "message": "El correo no está registrado. Por favor, escribe un correo válido.",
                        "state": "validar_correo",
                        "email": None
                    }, status=200)

            # **CASO 2:** Procesar intenciones después de la validación
            if estado == "procesar_intencion" and email:
                dueño = Dueño.objects.filter(correo=email).first()
                if not dueño:
                    # Reiniciar sesión si el usuario no se encuentra
                    request.session.flush()
                    return JsonResponse({
                        "error": "Dueño no encontrado. La sesión se ha reiniciado. Por favor, escribe tu correo electrónico nuevamente.",
                        "state": "validar_correo",
                        "email": None
                    }, status=404)

                # Identificar intención del mensaje
                intencion = identificar_intencion(mensaje)

                if intencion == "recordatorios":
                    return manejar_recordatorios(dueño, mensaje, email)
                elif intencion == "sugerencias_cuidados":
                    return manejar_sugerencias(dueño, mensaje, email)
                elif intencion == "consulta_medica":
                    return manejar_consultas(dueño, mensaje, email)
                else:
                    return JsonResponse({
                        "message": "No entendí tu solicitud. Por favor, intenta nuevamente.",
                        "state": "procesar_intencion",
                        "email": email
                    }, status=200)

            # **Estado desconocido**
            return JsonResponse({
                "error": "Estado inválido o faltante. Por favor, reintenta.",
                "state": estado,
                "email": email
            }, status=400)

        except json.JSONDecodeError:
            return JsonResponse({"error": "El cuerpo debe ser JSON válido."}, status=400)
        except Exception as e:
            return JsonResponse({"error": f"Error interno: {str(e)}"}, status=500)

    return JsonResponse({"error": "Método no permitido."}, status=405)



def identificar_intencion(mensaje):
    """
    Usa GPT para clasificar la intención del usuario basada en su mensaje.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un asistente para una clínica veterinaria. Tu tarea es analizar el mensaje del usuario y devolver únicamente "
                        "una clasificación de intención en una de las siguientes categorías: 'recordatorios', 'sugerencias_cuidados', "
                        "'consulta_medica', o 'desconocido'. Por favor, responde exclusivamente con la clasificación, sin texto adicional."
                        "Ten en cuenta el uso de sinonimos y palabras variadas que sirven para identificarse como alguna de las cuatro opciones"
                    ),
                },
                {"role": "user", "content": f"Mensaje del usuario: {mensaje}"},
            ],
            max_tokens=20,
        )

        # Registrar la respuesta para depuración
        print(f"Respuesta de GPT: {response}")

        # Extraer el contenido de la respuesta
        contenido = response.choices[0].message.content.strip().lower()

        # Validar si la respuesta contiene una de las categorías esperadas
        categorias = ['recordatorios', 'sugerencias_cuidados', 'consulta_medica', 'desconocido']
        for categoria in categorias:
            if categoria in contenido:
                return categoria

        # Si no coincide con ninguna categoría, devolver 'desconocido'
        return "desconocido"

    except Exception as e:
        print(f"Error en identificar_intencion: {e}")
        return "desconocido"

def manejar_recordatorios(dueño, mensaje, session):
    """
    Gestiona el flujo secuencial para listar mascotas, elegir una, y agregar/modificar recordatorios.
    """
    # Asegurarse de que `session` es un diccionario válido
    if not isinstance(session, dict):
        return JsonResponse({"error": "La sesión no es válida."}, status=500)

    email = session.get("email", None)
    estado = session.get("estado_recordatorio", "listar_mascotas")

    # **Paso 1: Listar Mascotas**
    if estado == "listar_mascotas":
        mascotas = Mascota.objects.filter(dueño=dueño)
        if not mascotas.exists():
            session.clear()  # Limpiar la sesión en caso de error
            return JsonResponse({
                "message": "No tienes mascotas registradas en el sistema. Por favor, regístralas primero.",
                "email": email
            })

        nombres_mascotas = ", ".join([m.nombre for m in mascotas])
        session["estado_recordatorio"] = "elegir_mascota"
        return JsonResponse({
            "message": f"Tienes las siguientes mascotas registradas: {nombres_mascotas}. Por favor, escribe el nombre de la mascota para continuar.",
            "email": email
        })

    # **Paso 2: Elegir Mascota**
    if estado == "elegir_mascota":
        mascotas = Mascota.objects.filter(dueño=dueño)
        mascota = identificar_mascota(mensaje, mascotas)
        if not mascota:
            return JsonResponse({
                "message": "No pude identificar la mascota mencionada. Por favor, escribe el nombre correctamente.",
                "email": email
            })

        # Guardar la mascota seleccionada en la sesión
        session["mascota_seleccionada"] = str(mascota.id_mascota)
        session["estado_recordatorio"] = "gestionar_tipo_recordatorio"
        return JsonResponse({
            "message": f"Has seleccionado a {mascota.nombre}. ¿Qué tipo de recordatorio deseas gestionar? (antiparasitario, antipulgas, vacuna)",
            "email": email
        })

    # **Paso 3: Gestionar Tipo de Recordatorio**
    if estado == "gestionar_tipo_recordatorio":
        mascota_id = session.get("mascota_seleccionada", None)
        if not mascota_id:
            session.clear()  # Limpiar la sesión en caso de error
            return JsonResponse({"error": "No se encontró la mascota seleccionada. Por favor, reinicia el proceso."}, status=400)

        mascota = Mascota.objects.get(id_mascota=mascota_id)
        tipo_recordatorio = identificar_tipo_recordatorio(mensaje)

        if tipo_recordatorio == "desconocido":
            return JsonResponse({
                "message": "No entendí el tipo de recordatorio que deseas gestionar. Por favor, especifica: antiparasitario, antipulgas o vacuna.",
                "email": email
            })

        # Verificar si ya existe un recordatorio
        recordatorio = Recordatorio.objects.filter(mascota=mascota, tipo=tipo_recordatorio).first()
        if recordatorio:
            # Actualizar fecha del recordatorio existente
            recordatorio.fecha = datetime.now().date() + timedelta(days=30)
            recordatorio.save()
            session.clear()  # Finalizar flujo
            return JsonResponse({
                "message": f"El recordatorio de {tipo_recordatorio} para {mascota.nombre} ha sido actualizado. La nueva fecha es el {recordatorio.fecha.strftime('%d/%m/%Y')}.",
                "email": email
            })

        # Crear un nuevo recordatorio
        nuevo_recordatorio = Recordatorio.objects.create(
            mascota=mascota,
            tipo=tipo_recordatorio,
            fecha=datetime.now().date() + timedelta(days=30),
            frecuencia="Mensual",
            canal="Chat",
            estado="Activo"
        )
        session.clear()  # Finalizar flujo
        return JsonResponse({
            "message": f"Se ha creado un nuevo recordatorio de {tipo_recordatorio} para {mascota.nombre}. La fecha es el {nuevo_recordatorio.fecha.strftime('%d/%m/%Y')}.",
            "email": email
        })

    # Estado desconocido
    return JsonResponse({"error": "Estado inválido o faltante en el flujo de recordatorios."}, status=400)

def identificar_mascota(mensaje, mascotas):
    """
    Identifica a la mascota mencionada en el mensaje del usuario.
    Si no se encuentra, usa GPT para intentar inferirla.
    """
    for mascota in mascotas:
        if mascota.nombre.lower() in mensaje.lower():
            return mascota

    # Usar GPT para inferir si el mensaje menciona incorrectamente una mascota
    prompt = (
        f"Tienes las siguientes mascotas registradas: {', '.join([m.nombre for m in mascotas])}. "
        f"El usuario escribió: '{mensaje}'. ¿Puedes identificar cuál mascota corresponde?"
    )
    sugerencia = consultar_gpt(prompt)
    for mascota in mascotas:
        if mascota.nombre.lower() in sugerencia.lower():
            return mascota

    return None

def identificar_tipo_recordatorio(mensaje):
    """
    Identifica el tipo de recordatorio basado en el mensaje del usuario.
    Usa GPT para clasificar si es antiparasitario, antipulgas, vacuna o desconocido.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un asistente veterinario. Tu tarea es identificar el tipo de recordatorio "
                        "que el usuario desea gestionar. Las opciones son: 'antiparasitario', 'antipulgas', 'vacuna'. "
                        "Responde solo con una de estas categorías o 'desconocido' si no queda claro."
                    ),
                },
                {"role": "user", "content": f"Mensaje del usuario: {mensaje}"},
            ],
            max_tokens=20,
        )
        contenido = response.choices[0].message.content.strip().lower()
        opciones = ["antiparasitario", "antipulgas", "vacuna", "desconocido"]
        return contenido if contenido in opciones else "desconocido"
    except Exception as e:
        print(f"Error en identificar_tipo_recordatorio: {e}")
        return "desconocido"

def consultar_gpt(prompt):
    """
    Realiza una consulta a GPT para ayudar a entender el mensaje del usuario.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Eres un asistente veterinario que ayuda a identificar solicitudes ambiguas. Respuestas cortas y consisas"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=50,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error al consultar GPT: {e}")
        return "desconocido"



def manejar_sugerencias(dueño, mensaje, email=None):
    """
    Genera sugerencias personalizadas basadas en las mascotas del dueño.
    """
    mascotas = Mascota.objects.filter(dueño=dueño)
    if not mascotas.exists():
        return JsonResponse({
            "message": "No tienes mascotas registradas en el sistema. Por favor, regístralas para recibir sugerencias personalizadas.",
            "email": email
        })

    # Intentar identificar la mascota mencionada en el mensaje
    mascota = identificar_mascota(mensaje, mascotas)
    if mascota:
        prompt = (
            f"El usuario necesita sugerencias de cuidado para su mascota {mascota.nombre}. "
            f"Detalles: especie {mascota.especie}, raza {mascota.raza}, edad aproximada {calcular_edad(mascota.nacimiento)} años."
        )
        sugerencias = consultar_gpt(prompt)
        return JsonResponse({"message": sugerencias, "email": email})

    return JsonResponse({"message": "No entendí a qué mascota te refieres. Por favor, indícame su nombre o una característica.", "email": email})

def manejar_consultas(dueño, mensaje, email=None):
    """
    Inicia una consulta médica para una mascota específica.
    """
    mascotas = Mascota.objects.filter(dueño=dueño)
    if not mascotas.exists():
        return JsonResponse({
            "message": "No tienes mascotas registradas. Por favor, regístralas para poder iniciar consultas médicas.",
            "email": email
        })

    # Intentar identificar la mascota mencionada en el mensaje
    mascota = identificar_mascota(mensaje, mascotas)
    if mascota:
        Consulta.objects.create(
            mascota=mascota,
            fecha_consulta=datetime.now().date(),
            motivo="Consulta iniciada desde el chatbot.",
            diagnóstico="",
            tratamiento=""
        )
        return JsonResponse({
            "message": f"Consulta médica iniciada para {mascota.nombre}. Un médico revisará esta información pronto.",
            "email": email
        })

    return JsonResponse({"message": "¿Para cuál de tus mascotas deseas iniciar una consulta médica?", "email": email})


def identificar_mascota(mensaje, mascotas):
    """
    Identifica a la mascota mencionada en el mensaje del usuario.
    """
    for mascota in mascotas:
        if mascota.nombre.lower() in mensaje.lower():
            return mascota
    return None


def calcular_edad(nacimiento):
    """
    Calcula la edad de una mascota en años.
    """
    hoy = datetime.now().date()
    edad_años = hoy.year - nacimiento.year
    if hoy.month < nacimiento.month or (hoy.month == nacimiento.month and hoy.day < nacimiento.day):
        edad_años -= 1
    return edad_años


def consultar_gpt(prompt):
    """
    Consulta a GPT para generar sugerencias personalizadas.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Eres un asistente experto en cuidados veterinarios."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=150,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Lo siento, hubo un problema al obtener las sugerencias: {e}"
