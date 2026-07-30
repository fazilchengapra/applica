from drf_spectacular.utils import OpenApiResponse, OpenApiExample

COMMON_AUTH_ERROR_RESPONSES = {
    404: OpenApiResponse(
        description="No user found with this email.",
        examples=[OpenApiExample("Not found", value={"detail": "User not found."})],
    ),
    429: OpenApiResponse(
        description="Too many requests sent recently; cooldown in effect.",
        examples=[
            OpenApiExample(
                "Cooldown", value={"detail": "Please wait before trying again."}
            )
        ],
    ),
    500: OpenApiResponse(
        description="Unexpected server error.",
        examples=[
            OpenApiExample(
                "Server error", value={"detail": "An unexpected error occurred."}
            )
        ],
    ),
}
