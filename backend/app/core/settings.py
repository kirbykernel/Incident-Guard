# ============================================================
# IncidentGuard — configurações centralizadas
# Todas as variáveis de ambiente são lidas aqui.
# Pydantic-settings valida tipos e levanta erro na inicialização
# se algo obrigatório estiver faltando — fail fast, fail loud.
# ============================================================

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Aplicação ---
    API_ENV: str = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    LOG_LEVEL: str = "info"

    # --- Banco de dados ---
    DATABASE_URL: str

    # --- JWT ---
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480

    # --- API Keys (webhooks) ---
    ALERTMANAGER_API_KEY: str
    SECURITY_SCANNER_API_KEY: str
    FALCO_API_KEY: str

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def jwt_secret_must_be_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY deve ter ao menos 32 caracteres")
        if v == "changeme-generate-with-openssl-rand-hex-32":
            raise ValueError("JWT_SECRET_KEY não pode ser o valor padrão do .env.example")
        return v

    @field_validator("API_ENV")
    @classmethod
    def api_env_must_be_valid(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"API_ENV deve ser um de: {allowed}")
        return v

    @property
    def is_production(self) -> bool:
        return self.API_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Retorna instância cacheada das configurações.
    lru_cache garante que o .env é lido apenas uma vez.
    Use como dependência FastAPI: Depends(get_settings)
    """
    return Settings()