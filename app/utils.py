from twilio.rest import Client
from django.conf import settings
from django.core.mail import send_mail
def formato_numero_chileno(numero):
    # Verifica si el número ya tiene el prefijo +56
    if numero.startswith("+56"):
        return numero  # Devuelve el número sin cambios si ya está en formato +56
    # Si el número comienza con 9 y tiene 9 dígitos, agrega el prefijo +56
    elif numero.startswith("9") and len(numero) == 9:
        return f"+56{numero}"
    else:
        # Si el número no cumple con el formato esperado, puedes manejar el error o dejarlo como está
        raise ValueError("Número de teléfono no válido. Debe comenzar con +56 o ser un número de 9 dígitos que comienza con 9.")






def enviar_mensaje_whatsapp(to, message):
    # Inicializa el cliente de Twilio con las credenciales
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    
    # Intenta enviar el mensaje de WhatsApp
    try:
        message = client.messages.create(
            body=message,  # Contenido del mensaje
            from_=settings.TWILIO_WHATSAPP_NUMBER,  # Número de WhatsApp del remitente
            to=f'whatsapp:{to}'  # Número de destino 
        )
        print("Mensaje enviado con SID:", message.sid)  
        return message.sid  
    except Exception as e:
        print(f"Error al enviar el mensaje de WhatsApp: {e}")  # Imprime el error en la consola para depuración
        return None 

def enviar_correo_electronico(destinatario, asunto, mensaje):
    try:
        send_mail(
            asunto,  # Asunto del correo
            mensaje,  # Cuerpo del mensaje
            settings.EMAIL_HOST_USER,  # Remitente (correo configurado)
            [destinatario],  # Lista de destinatarios
            fail_silently=False,
        )
        print("Correo enviado exitosamente a:", destinatario)
        return True
    except Exception as e:
        print(f"Error al enviar el correo electrónico: {e}")
        return False