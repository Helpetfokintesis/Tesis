import os
import openai 
import datetime
from openai import OpenAIError
from django.shortcuts import render
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from app.models import Mascota, Recordatorio, UsuarioSistema,Dueño, Consulta
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from dotenv import load_dotenv
from django.http import JsonResponse
import json
from django.contrib.auth.decorators import login_required
from django.middleware.csrf import get_token
from django.contrib.auth.models import  User
from django.contrib.sessions.models import Session
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import authentication_classes, permission_classes


# Load the API key from the .env file
# Load environment variables
load_dotenv("/home/ubuntu/Tesis/helpet/api_chat/api_key.env")

# Set OpenAI API key
api_key = os.getenv("api_key")

class ChatBotVeterinaria:
    def __init__(self, usuario):
        self.usuario = usuario
        self.estado_actual = "inicio"
        self.contexto_actual = None

    def manejar_respuesta(self, entrada_usuario):
        entrada_usuario = entrada_usuario.lower()

        if self.estado_actual == "inicio":
            return self.iniciar_conversacion()

        if "recordatorio" in entrada_usuario:
            self.contexto_actual = "recordatorios"
            return self.gestionar_recordatorios(entrada_usuario)

        if "sugerencia" in entrada_usuario or "cuidado" in entrada_usuario:
            self.contexto_actual = "sugerencias_cuidados"
            return self.gestionar_sugerencias(entrada_usuario)

        if "consulta" in entrada_usuario or "médico" in entrada_usuario:
            self.contexto_actual = "consulta_medica"
            return self.gestionar_consultas(entrada_usuario)

        if "salir" in entrada_usuario:
            self.estado_actual = "inicio"
            return "Gracias por usar HelPet. ¡Hasta pronto!"

        return "Lo siento, no entendí tu solicitud. ¿Puedes intentarlo nuevamente?"

    def iniciar_conversacion(self):
        self.estado_actual = "activo"
        return (
            f"¡Hola, {self.usuario.nombre}! Bienvenido a HelPet. ¿En qué puedo ayudarte hoy? "
            "Opciones: "
            "1. Ver recordatorios. "
            "2. Sugerencias de cuidados. "
            "3. Iniciar una consulta médica."
        )

    def gestionar_recordatorios(self, entrada_usuario):
        mascotas = Mascota.objects.filter(dueño=self.usuario)
        if not mascotas.exists():
            return "No tienes mascotas registradas en el sistema. Por favor, regístralas para gestionar sus recordatorios."

        mascota = self.identificar_mascota(entrada_usuario, mascotas)
        if mascota:
            recordatorios = Recordatorio.objects.filter(mascota=mascota)
            if recordatorios.exists():
                respuesta = f"Estos son los recordatorios para {mascota.nombre}:\n"
                for rec in recordatorios:
                    respuesta += f"- {rec.tipo}: {rec.fecha} (Frecuencia: {rec.frecuencia}).\n"
                return respuesta
            else:
                return f"{mascota.nombre} no tiene recordatorios registrados."

        return "¿Puedes especificar para cuál de tus mascotas necesitas los recordatorios?"

    def gestionar_sugerencias(self, entrada_usuario):
        mascotas = Mascota.objects.filter(dueño=self.usuario)
        if not mascotas.exists():
            return "No tienes mascotas registradas. Por favor, regístralas para recibir sugerencias personalizadas."

        mascota = self.identificar_mascota(entrada_usuario, mascotas)
        if mascota:
            prompt = (
                f"Dame sugerencias de cuidado específicas para una mascota de tipo {mascota.especie}, "
                f"raza {mascota.raza}, con edad aproximada de {self.calcular_edad(mascota.nacimiento)}."
            )
            return f"Sugerencias para {mascota.nombre}:\n{self.consultar_gpt(prompt)}"

        return "No entendí a qué mascota te refieres. Por favor, indícame su nombre o una característica."

    def gestionar_consultas(self, entrada_usuario):
        mascotas = Mascota.objects.filter(dueño=self.usuario)
        if not mascotas.exists():
            return "No tienes mascotas registradas. Regístralas para poder iniciar una consulta médica."

        mascota = self.identificar_mascota(entrada_usuario, mascotas)
        if mascota:
            Consulta.objects.create(
                mascota=mascota,
                fecha_consulta=datetime.now().date(),
                motivo="Consulta iniciada desde el chatbot.",
                diagnóstico="",
                tratamiento=""
            )
            return f"Consulta médica iniciada para {mascota.nombre}. Un médico revisará esta información pronto."

        return "¿Para cuál de tus mascotas deseas iniciar una consulta médica?"

    def identificar_mascota(self, entrada_usuario, mascotas):
        for mascota in mascotas:
            if mascota.nombre.lower() in entrada_usuario:
                return mascota
        return None

    def consultar_gpt(self, prompt):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Eres un asistente experto en cuidados veterinarios."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=150,
            )
            return response['choices'][0]['message']['content']
        except Exception as e:
            return "Lo siento, hubo un problema al obtener las sugerencias."

    def calcular_edad(self, nacimiento):
        hoy = datetime.now().date()
        edad_años = hoy.year - nacimiento.year
        edad_meses = hoy.month - nacimiento.month
        if edad_meses < 0:
            edad_años -= 1
            edad_meses += 12
        return f"{edad_años} años y {edad_meses} meses"


def verificar_usuario_manual(request):
    """
    Verifica manualmente si un usuario está autenticado.
    """
    if not request.user.is_authenticated:
        # Retorna una tupla indicando el error
        return None, "El usuario no está autenticado o la sesión ha expirado."

    resultado = {
        "username": request.user.username,
        "email": request.user.email,
        "is_authenticated": True,
    }
    print(f"verificar_usuario_manual: {resultado}")
    return resultado, None

def obtener_datos_usuario(request):
    try:
        # Obtener los datos del usuario
        usuario_info, error = verificar_usuario_manual(request)
        
        if error:
            print(f"Error en verificar_usuario_manual: {error}")  # Debugging
            return None, error  # Retornar el error si ocurre

        print(f"Usuario obtenido: {usuario_info}")  # Debugging

        # Buscar el dueño en la base de datos
        dueño = Dueño.objects.get(correo=usuario_info["email"])  # Usar email en lugar de username si corresponde

        # Retornar los datos del dueño
        return {
            "dueño": {
                "nombre": dueño.nombre,
                "apellidos": dueño.apellidos,
                "teléfono": dueño.teléfono,
                "dirección": dueño.dirección,
                "ciudad": dueño.ciudad,
                "país": dueño.país,
                "región": dueño.región,
            }
        }, None

    except Dueño.DoesNotExist:
        return None, "No se encontró un dueño asociado al correo del usuario."

    except Exception as e:
        print(f"Error en obtener_datos_usuario: {str(e)}")  # Debugging
        return None, f"Error al obtener datos del usuario: {str(e)}"



@csrf_exempt

@csrf_exempt
def chatbot_kommunicate(request):
    if request.method == "POST":
        try:
            # Decodificar el JSON recibido del webhook
            data = json.loads(request.body.decode("utf-8"))

            # Extraer información importante
            message = data.get("message", "").strip()
            event_name = data.get("eventName", "").strip()

            # Usar la función auxiliar para obtener los datos del usuario
            datos_usuario, error = obtener_datos_usuario(request)

            if error:
                print(f"Error al obtener datos del usuario: {error}")  # Debugging
                # Si hay un error, responder con el mensaje correspondiente
                return JsonResponse([{"message": error}], safe=False)

            # Extraer dueño de los datos obtenidos
            dueño = datos_usuario["dueño"]

            # Crear una instancia del chatbot para el usuario autenticado
            chatbot = ChatBotVeterinaria(dueño)

            # Manejo de eventos específicos
            if event_name == "WELCOME":
                return JsonResponse([{
                    "message": f"¡Hola {dueño['nombre']}! Bienvenido a HelPet. ¿En qué puedo ayudarte hoy? Opciones: Recordatorios, Sugerencias, Consultas."
                }], safe=False)

            # Procesar mensaje normal
            if message:
                response_message = chatbot.manejar_respuesta(message)
                return JsonResponse([{"message": response_message}], safe=False)

        except Exception as e:
            # Manejar errores generales
            print(f"Error en chatbot_kommunicate: {str(e)}")  # Debugging
            return JsonResponse({"error": f"Error procesando la solicitud: {str(e)}"}, status=500)

    return JsonResponse({"error": "Método no permitido"}, status=405)


@login_required
def verificar_usuario_json(request):
    """
    Devuelve los datos del usuario autenticado en formato JSON.
    """
    csrf_token = get_token(request)  # Genera el token CSRF
    return JsonResponse({
        "username": request.user.username,
        "email": request.user.email,
        "is_authenticated": request.user.is_authenticated,
        "csrf_token": csrf_token
    })