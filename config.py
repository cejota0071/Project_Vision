from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Banco
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Inference
    INFERENCE_URL: str = "http://localhost:8000"

    # Storage
    UPLOAD_DIR: Path = Path("./storage/imagens")
    PDF_DIR: Path    = Path("./storage/laudos")

    # App
    APP_NAME: str    = "GREG Retinopatia"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool      = False

    class Config:
        env_file = ".env"


settings = Settings()

# Garante que os diretórios existam
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.PDF_DIR.mkdir(parents=True, exist_ok=True)