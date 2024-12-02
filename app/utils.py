from twilio.rest import Client
from django.conf import settings
from django.core.mail import send_mail

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


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



def enviar_mensaje_whatsapp(numero, mensaje):
    """
    Envía un mensaje de WhatsApp usando WhatsApp Web y Selenium.

    Args:
        numero (str): Número de teléfono en formato internacional (Ej: +56912345678).
        mensaje (str): Mensaje a enviar.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--user-data-dir=./chrome_data")  # Mantiene la sesión activa
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=options)

    try:
        # Abrir WhatsApp Web
        driver.get("https://web.whatsapp.com")
        print("Escanea el código QR si es la primera vez.")
        time.sleep(30)  
        # Espera explícita para que el campo de búsqueda de chat esté disponible
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.XPATH, "//div[@title='Buscar o empezar un chat']")))

        # Buscar el campo de búsqueda de contactos
        search_box = driver.find_element(By.XPATH, "//div[@title='Buscar o empezar un chat']")
        search_box.click()
        search_box.send_keys(numero)
        search_box.send_keys(Keys.ENTER)
        time.sleep(2)

        # Espera para que el campo de mensaje esté listo
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.XPATH, "//div[@title='Escribe un mensaje aquí']")))

        # Buscar el cuadro de mensaje y enviar el mensaje
        message_box = driver.find_element(By.XPATH, "//div[@title='Escribe un mensaje aquí']")
        message_box.click()
        message_box.send_keys(mensaje)
        message_box.send_keys(Keys.ENTER)

        print(f"Mensaje enviado a {numero} exitosamente.")

    except Exception as e:
        print(f"Error al enviar el mensaje de WhatsApp: {e}")

    finally:
        driver.quit()




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