from django.http import HttpResponsePermanentRedirect


class NormalizeSlashMiddleware:
    """
    Middleware que asegura que las URLs no terminen con barras duplicadas.
    Si una URL tiene doble barra (//), redirige permanentemente a la versión corregida.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if "//" in path:
            normalized_path = path.replace("//", "/")
            return HttpResponsePermanentRedirect(normalized_path)

        response = self.get_response(request)
        return response
    
from django.urls import resolve, Resolver404

class BlockExternalUrlsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            # Intenta resolver la URL solicitada
            resolve(request.path)
        except Resolver404:
            # Si no está en las rutas definidas, devuelve 404
            from django.http import HttpResponseNotFound
            return HttpResponseNotFound("<h1>404 Not Found</h1>")
        # Si la URL está definida, continúa con el flujo normal
        return self.get_response(request)