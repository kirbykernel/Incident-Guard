# ============================================================
# IncidentGuard — segurança: JWT e hashing de senhas
# ============================================================

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.settings import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer()


# ----------------------------------------------------------
# Hashing de senha com bcrypt
# ----------------------------------------------------------

def hash_password(plain: str) -> str:
    """Retorna hash bcrypt da senha em texto plano."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain.encode(), salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica se senha em texto plano corresponde ao hash."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ----------------------------------------------------------
# JSON Web Tokens
# ----------------------------------------------------------

def create_access_token(subject: str | Any, extra: dict = {}) -> str:
    """
    Gera JWT de acesso.
    - subject: identificador do usuário (geralmente o UUID)
    - extra: campos adicionais (ex: role)
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        **extra,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """
    Decodifica e valida JWT.
    Levanta HTTPException 401 em caso de token inválido ou expirado.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ----------------------------------------------------------
# Dependências FastAPI
# ----------------------------------------------------------

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> str:
    """
    Dependência FastAPI: extrai e valida o JWT do header Authorization.
    Retorna o UUID do usuário autenticado.

    Uso:
        @router.get("/me")
        async def me(user_id: str = Depends(get_current_user_id)):
            ...
    """
    payload = decode_access_token(credentials.credentials)
    user_id: str | None = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sem identificador de usuário",
        )
    return user_id


async def get_current_user_role(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> str:
    """
    Dependência FastAPI: retorna a role do usuário autenticado.
    Usado para autorização baseada em papéis (RBAC).
    """
    payload = decode_access_token(credentials.credentials)
    return payload.get("role", "viewer")


def verify_api_key(api_key: str, source: str) -> bool:
    """
    Valida API Key de serviços externos (webhooks).
    Compara com as chaves configuradas por fonte.
    """
    key_map = {
        "alertmanager": settings.ALERTMANAGER_API_KEY,
        "security_scanner": settings.SECURITY_SCANNER_API_KEY,
        "falco": settings.FALCO_API_KEY,
    }
    expected = key_map.get(source)
    if not expected:
        return False
    # Comparação segura contra timing attacks
    return bcrypt.checkpw(api_key.encode(), bcrypt.hashpw(expected.encode(), bcrypt.gensalt()))