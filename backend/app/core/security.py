# ============================================================
# IncidentGuard — segurança: JWT e hashing de senhas
# ============================================================

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import HTTPException, Request, status

from app.core.settings import get_settings

settings = get_settings()

# Cookies da sessão humana (JWT nunca fica acessível a JavaScript — ver
# routes/auth.py). ACCESS_TOKEN_COOKIE é httpOnly; CSRF_TOKEN_COOKIE não,
# pois o frontend precisa lê-lo para ecoar em CSRF_HEADER (double-submit).
ACCESS_TOKEN_COOKIE = "access_token"
CSRF_TOKEN_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"


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
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )


# ----------------------------------------------------------
# CSRF (double-submit cookie)
# ----------------------------------------------------------

def generate_csrf_token() -> str:
    """Token aleatório opaco — não precisa ser assinado nem persistido.

    A proteção do double-submit vem da Same-Origin Policy: um site
    atacante não consegue ler CSRF_TOKEN_COOKIE para replicar o valor
    no header de uma requisição forjada.
    """
    return secrets.token_urlsafe(32)


def verify_csrf_token(request: Request) -> None:
    """
    Dependência FastAPI para rotas que alteram estado (POST/PATCH/DELETE)
    autenticadas por cookie. Exige que o valor do cookie CSRF bata com o
    header X-CSRF-Token — um atacante cross-site não tem como ler o
    cookie para reproduzir esse valor no header.
    """
    cookie_token = request.cookies.get(CSRF_TOKEN_COOKIE)
    header_token = request.headers.get(CSRF_HEADER)

    if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token inválido ou ausente",
        )


# ----------------------------------------------------------
# Dependências FastAPI
# ----------------------------------------------------------

async def get_current_user_id(request: Request) -> str:
    """
    Dependência FastAPI: extrai e valida o JWT do cookie httpOnly.
    Retorna o UUID do usuário autenticado.

    Uso:
        @router.get("/me")
        async def me(user_id: str = Depends(get_current_user_id)):
            ...
    """
    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado",
        )

    payload = decode_access_token(token)
    user_id: str | None = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sem identificador de usuário",
        )
    return user_id


async def get_current_user_role(request: Request) -> str:
    """
    Dependência FastAPI: retorna a role do usuário autenticado.
    Usado para autorização baseada em papéis (RBAC).
    """
    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado",
        )
    payload = decode_access_token(token)
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