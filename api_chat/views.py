import os
import jwt
from dotenv import load_dotenv
from openai import OpenAI
from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings
from app.models import UsuarioSistema, Mascota, Recordatorio, Consulta
from datetime import datetime
import json
from .utils import generate_access_token
from datetime import datetime, timedelta

# Clave secreta para firmar los tokens
SECRET_KEY = settings.SECRET_KEY

load_dotenv()
client = OpenAI(api_key = os.getenv('OPENAI_API_KEY'))  


@login_required
def index(request):
    # Generar el token de acceso para el usuario autenticado
    user = request.user
    access_token = generate_access_token(user.id)  # Suponiendo que usas el ID del usuario para el token

    # Pasar el token a la plantilla
    context = {
        "user_id": user.id,
        "user_email": user.email,
        "access_token": access_token,
    }
    return render(request, "index.html", context)

@login_required
def verificar_usuario_chat(request):
    """
    Verifica si el usuario está autenticado y validado antes de iniciar el chat.
    """
    if not request.user.is_active:  # O usa un campo personalizado para la verificación
        messages.error(request, "Tu cuenta no está verificada. Verifica tu correo.")
        return redirect('verificacionPendiente')  # Redirigir a una página de verificación

    # Usuario verificado, redirigir al chat
    return redirect(reverse('chat_view'))

class ChatBotVeterinaria:
    def __init__(self, usuario_sistema):
        self.usuario = usuario_sistema
        self.estado_actual = "inicio"
        self.contexto_actual = None

    def manejar_respuesta(self, entrada_usuario):
        """
        Procesa la entrada del usuario y dirige la conversación según el contexto usando GPT.
        """
        if not self.usuario:
            return "Parece que eres un usuario anónimo. Puedes registrarte para obtener una experiencia más personalizada."

        intencion = self.obtener_intencion_gpt(entrada_usuario)

        if "recordatorios" in intencion.lower():
            self.contexto_actual = "recordatorios"
            return self.gestionar_recordatorios(entrada_usuario)

        elif "sugerencias_cuidados" in intencion.lower():
            self.contexto_actual = "sugerencias_cuidados"
            return self.gestionar_sugerencias(entrada_usuario)

        elif "consulta_medica" in intencion.lower():
            self.contexto_actual = "consulta_medica"
            return self.gestionar_consultas(entrada_usuario)

        return "Lo siento, no entendí tu solicitud. ¿Puedes intentar nuevamente?"

    def obtener_intencion_gpt(self, prompt):
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
                            "Eres un asistente para una clínica veterinaria. Tu tarea es clasificar "
                            "las intenciones del usuario en las siguientes categorías: 'recordatorios', "
                            "'sugerencias_cuidados', 'consulta_medica', o 'desconocido'. Además, responde directamente si es necesario."
                        ),
                    },
                    {"role": "user", "content": f"Mensaje del usuario: {prompt}"},
                ],
                max_tokens=100,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error al determinar la intención: {str(e)}"

    def gestionar_recordatorios(self, entrada_usuario):
        """
        Proporciona información sobre los recordatorios de las mascotas del usuario.
        """
        if not self.usuario:
            return "Registra tus datos para poder gestionar los recordatorios de tus mascotas."

        mascotas = Mascota.objects.filter(dueño__correo=self.usuario.correo)
        if not mascotas.exists():
            return "No tienes mascotas registradas en el sistema. Por favor, regístralas para gestionar sus recordatorios."

        mascota = self.identificar_mascota(entrada_usuario, mascotas)
        if mascota:
            recordatorios = Recordatorio.objects.filter(mascota=mascota)
            if recordatorios.exists():
                return f"Estos son los recordatorios para {mascota.nombre}: " + ", ".join(
                    [f"{rec.tipo} el {rec.fecha}" for rec in recordatorios]
                )
            else:
                return f"{mascota.nombre} no tiene recordatorios registrados."

        return "¿Puedes especificar para cuál de tus mascotas necesitas los recordatorios?"

    def gestionar_sugerencias(self, entrada_usuario):
        """
        Ofrece sugerencias personalizadas usando GPT según la mascota seleccionada.
        """
        mascotas = Mascota.objects.filter(dueño__correo=self.usuario.correo)
        if not mascotas.exists():
            return "No tienes mascotas registradas. Por favor, regístralas para recibir sugerencias personalizadas."

        mascota = self.identificar_mascota(entrada_usuario, mascotas)
        if mascota:
            prompt = (
                f"El usuario {self.usuario.nombre} busca sugerencias de cuidado para su mascota {mascota.nombre}. "
                f"Detalles: especie {mascota.especie}, raza {mascota.raza}, edad aproximada de {self.calcular_edad(mascota.nacimiento)}."
            )
            return self.consultar_gpt(prompt)

        return "No entendí a qué mascota te refieres. Por favor, indícame su nombre o una característica."

    def gestionar_consultas(self, entrada_usuario):
        """
        Gestiona o inicia consultas médicas.
        """
        mascotas = Mascota.objects.filter(dueño__correo=self.usuario.correo)
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
        """
        Identifica a la mascota mencionada en la entrada del usuario.
        """
        for mascota in mascotas:
            if mascota.nombre.lower() in entrada_usuario:
                return mascota
        return None

    def consultar_gpt(self, prompt):
        """
        Realiza una consulta a GPT usando el nuevo formato de la API OpenAI.
        """
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Eres un asistente experto en cuidados veterinarios."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=150,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except openai.error.OpenAIError as e:
            return f"Lo siento, hubo un problema al obtener las sugerencias: {e}"
        except Exception as e:
            return "Ocurrió un error inesperado. Por favor, inténtalo más tarde."


    def calcular_edad(self, nacimiento):
        """
        Calcula la edad de una mascota en años y meses.
        """
        hoy = datetime.now().date()
        edad_años = hoy.year - nacimiento.year
        edad_meses = hoy.month - nacimiento.month
        if edad_meses < 0:
            edad_años -= 1
            edad_meses += 12
        return f"{edad_años} años y {edad_meses} meses"


#@csrf_exempt
def chatbot_kommunicate(request):
    """
    Maneja las solicitudes del bot de Kommunicate y asegura la autenticación del usuario.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            message = data.get("message", "")
            event_name = data.get("eventName", "")
            metadata = data.get("metadata", {})

            # Extraer datos de usuario del metadata
            user_name = metadata.get("name", None)
            user_email = metadata.get("email", None)

            # Validar y buscar al usuario en la base de datos
            usuario_sistema = None
            if user_email:
                usuario_sistema = UsuarioSistema.objects.filter(correo=user_email).first()

            # Instanciar el chatbot
            chatbot = ChatBotVeterinaria(usuario_sistema)

            # Evento de bienvenida
            if event_name == "WELCOME":
                return JsonResponse([{
                    "message": f"¡Hola {user_name}! Bienvenido a HelPet. ¿En qué puedo ayudarte?"
                }], safe=False)

            # Procesar mensaje del usuario
            if message:
                response_message = chatbot.manejar_respuesta(message)
                return JsonResponse([{"message": response_message}], safe=False)

        except Exception as e:
            # Manejar errores
            return JsonResponse({"error": f"Error procesando la solicitud: {str(e)}"}, status=500)

    if request.method == "GET":
        return JsonResponse({
            "message": "Bienvenido al chatbot de HelPet.",
            "instructions": "Usa este endpoint para interactuar con el chatbot.",
            "example_POST": {
                "message": "¿Cuáles son los recordatorios de mis mascotas?",
                "eventName": "",
                "metadata": {
                    "name": "Juan",
                    "email": "juan@example.com"
                }
            },
            "note": "Envíe una solicitud POST con los datos necesarios para interactuar."
        })

    # Responder a otros métodos no permitidos
    return JsonResponse({"error": "Método no permitido"}, status=405)

