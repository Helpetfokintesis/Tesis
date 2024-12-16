import jwt
from datetime import datetime, timedelta
from django.conf import settings

def generate_access_token(user_id):
    """
    Genera un token de acceso JWT para el usuario.
    
    Args:
        user_id (int): El ID del usuario.
    
    Returns:
        str: Token de acceso firmado.
    """
    # Configurar la expiración del token
    expiration = datetime.utcnow() + timedelta(days=1)  # Token válido por 1 día

    # Crear el payload del token
    payload = {
        "userId": user_id,  # Identificador único del usuario
        "exp": expiration,  # Fecha de expiración
        "iat": datetime.utcnow(),  # Fecha de emisión
    }

    # Firmar el token usando SECRET_KEY de settings.py
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token