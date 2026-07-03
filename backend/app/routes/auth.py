# ============================================================
# IncidentGuard — rotas de autenticação
# POST /auth/login  → autentica e define cookies de sessão (JWT + CSRF)
# POST /auth/logout → limpa os cookies de sessão
# POST /auth/signup → cria usuário (apenas admin em produção)
# GET  /auth/me     → retorna usuário autenticado
#
# Sessão via cookie httpOnly, não Authorization header: o JWT nunca fica
# acessível a JavaScript no navegador (ver core/security.py e
# docs/uml/threat-model-stride.md).
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    ACCESS_TOKEN_COOKIE,
    CSRF_TOKEN_COOKIE,
    create_access_token,
    generate_csrf_token,
    get_current_user_id,
    hash_password,
    verify_password,
)
from app.core.settings import get_settings
from app.models.models import User
from app.schemas.schemas import (
    LoginRequest,
    UserCreate,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _set_session_cookies(response: Response, user: User) -> None:
    token = create_access_token(
        subject=str(user.id),
        extra={"role": user.role.value, "email": user.email},
    )
    csrf_token = generate_csrf_token()
    max_age = settings.JWT_EXPIRE_MINUTES * 60

    response.set_cookie(
        ACCESS_TOKEN_COOKIE,
        token,
        max_age=max_age,
        path="/",
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
    )
    # Não httpOnly de propósito: o frontend precisa ler esse valor para
    # ecoá-lo no header X-CSRF-Token (double-submit) — ver core/security.py.
    response.set_cookie(
        CSRF_TOKEN_COOKIE,
        csrf_token,
        max_age=max_age,
        path="/",
        httponly=False,
        secure=settings.is_production,
        samesite="lax",
    )


@router.post("/login", response_model=UserResponse)
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """
    Autentica usuário com email e senha.
    Define cookies de sessão (JWT httpOnly + CSRF token); o corpo da
    resposta nunca carrega o token — se carregasse, um XSS interceptando
    a resposta do fetch teria o mesmo acesso que teria via localStorage.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Mensagem genérica — não revela se o email existe ou não
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta desativada",
        )

    _set_session_cookies(response, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    """
    Encerra a sessão. Um cookie httpOnly só pode ser removido pelo
    servidor — daí este endpoint existir, em vez de o frontend apenas
    "esquecer" um valor local.
    """
    response.delete_cookie(ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(CSRF_TOKEN_COOKIE, path="/")


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Cria novo usuário.
    Em produção, este endpoint deve ser protegido por autenticação de admin.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email já cadastrado",
        )

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.get("/me", response_model=UserResponse)
async def me(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Retorna dados do usuário autenticado."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    return user