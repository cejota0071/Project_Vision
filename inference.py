import httpx
from fastapi import HTTPException
from backend.config import settings


async def chamar_inferencia(imagem_bytes: bytes, filename: str) -> dict:
    """
    Envia a imagem ao servidor de inferência (greg_retina_inference.py)
    e retorna o resultado já parseado.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.INFERENCE_URL}/predict",
                files={"file": (filename, imagem_bytes, "image/jpeg")},
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(503, "Servidor de inferência indisponível.")
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao chamar inferência.")
    except httpx.HTTPStatusError as e:
        raise HTTPException(502, f"Erro no servidor de inferência: {e.response.text}")


async def status_inferencia() -> dict:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.INFERENCE_URL}/status")
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return {"status": "offline", "modelo_carregado": False}