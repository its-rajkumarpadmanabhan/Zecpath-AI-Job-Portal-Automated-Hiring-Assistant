from django.http import JsonResponse


def home(request):
    """
    Home API endpoint.
    Returns a simple JSON greeting to confirm the backend is running.
    """
    return JsonResponse({"message": "Hello Zecpath Backend"})
