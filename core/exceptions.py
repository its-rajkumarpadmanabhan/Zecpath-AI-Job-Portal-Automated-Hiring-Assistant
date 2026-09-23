from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    # Call DRF's default exception handler first to get the standard response
    response = exception_handler(exc, context)

    if response is not None:
        custom_data = {
            "status": "error",
            "code": response.status_code,
            "message": "An error occurred while processing your request.",
            "errors": response.data,
        }

        # Format specific status codes with cleaner contextual messages
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            custom_data["message"] = "Invalid payload or validation failed."
        elif response.status_code == status.HTTP_401_UNAUTHORIZED:
            custom_data["message"] = "Authentication credentials were not provided or are invalid."
        elif response.status_code == status.HTTP_403_FORBIDDEN:
            custom_data["message"] = "You do not have permission to perform this action."
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            custom_data["message"] = "The requested resource was not found."

        response.data = custom_data
    else:
        # Handle unhandled 500 internal server errors cleanly without crashing/leaking code details
        response = Response(
            {
                "status": "error",
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error. Please try again later.",
                "errors": str(exc),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
