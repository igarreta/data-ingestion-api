from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.config import settings

_bearer = HTTPBearer()


def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
) -> str:
    """Validate Bearer token and return the app name associated with it."""
    tokens = settings.get_tokens()
    app_name = tokens.get(credentials.credentials)
    if app_name is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
        )
    return app_name
