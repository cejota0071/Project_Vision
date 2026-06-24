"""
GREG Retina — Script de Inferência FastAPI
==========================================
Modelo : EfficientNet-B3 + CBAM, treinado no APTOS 2019
Classes: 0 = Sem Retinopatia  |  1 = Retinopatia Leve/Moderada  |  2 = Retinopatia Grave/Proliferativa
Checkpoint: best_model.pt  (época 56, val_acc = 92.08%)
"""

import io
import os
import time
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional


import torch
import torch.nn as nn
import torchvision.transforms as T
from torchvision.models import efficientnet_b3
from PIL import Image
import numpy as np

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ─────────────────────────────────────────────
# Configuração de logging
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("greg_retina")

# ─────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────
# Resolução do caminho do modelo
# Prioridade:
#   1. Variável de ambiente GREG_MODEL_PATH
#   2. Relativo ao próprio script:
#      <pasta_do_script>/experiments/greg_retina_output_v3/checkpoints/best_model.pt
#   3. Caminho absoluto hardcoded do projeto (Windows / Linux)
# ─────────────────────────────────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent

_CHECKPOINT_CANDIDATES = [
    # 1. Variável de ambiente (maior prioridade)
    Path(os.environ["GREG_MODEL_PATH"]) if "GREG_MODEL_PATH" in os.environ else None,
    # 2. Relativo ao script — estrutura padrão do projeto
    _SCRIPT_DIR / "experiments" / "greg_retina_output_v3" / "checkpoints" / "best_model.pt",
    # 3. Dois níveis acima do script (caso o script esteja em src/ ou similar)
    _SCRIPT_DIR.parent / "experiments" / "greg_retina_output_v3" / "checkpoints" / "best_model.pt",
    # 4. Path absoluto hardcoded do projeto (ajuste se mover o projeto)
    Path(r"C:\\projetos\\web-css3\\experiments\\greg_retina_output_v3\\checkpoints\\best_model.pt"),
    # 5. Fallback: mesma pasta do script
    _SCRIPT_DIR / "best_model.pt",
]

MODEL_PATH: Path = next(
    (p for p in _CHECKPOINT_CANDIDATES if p is not None and p.exists()),
    _CHECKPOINT_CANDIDATES[1],
)

GREG_MODEL_DRIVE_URL: str = os.environ.get(
    "GREG_MODEL_DRIVE_URL",
    "https://drive.google.com/file/d/18ba1nNEp1GCqJDtlgFiYeyhbdWAnLvPD/view?usp=drive_link",
)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
IMG_SIZE = 300
TEMPERATURE = 1.50
NUM_CLASSES = 3

CLASSES = {
    0: "Sem Retinopatia Diabética",
    1: "Retinopatia Leve / Moderada",
    2: "Retinopatia Grave / Proliferativa",
}

RISCO = {
    0: "baixo",
    1: "moderado",
    2: "alto",
}

CONDUTA = {
    0: "Retorno anual de rotina. Controle glicêmico e pressórico.",
    1: "Encaminhamento a oftalmologista em até 30 dias para avaliação complementar.",
    2: "Encaminhamento URGENTE a oftalmologista. Risco de perda visual.",
}

# ─────────────────────────────────────────────
# Arquitetura
# ─────────────────────────────────────────────


class ChannelAttention(nn.Module):
    def __init__(self, channels: int, reduction: int = 16):
        super().__init__()
        self.fc = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(channels, channels // reduction, bias=False),
            nn.ReLU(),
            nn.Linear(channels // reduction, channels, bias=False),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        w = self.fc(x).unsqueeze(-1).unsqueeze(-1)
        return x * w


class SpatialAttention(nn.Module):
    def __init__(self, kernel_size: int = 7):
        super().__init__()
        self.conv = nn.Conv2d(2, 1, kernel_size, padding=kernel_size // 2, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        avg = x.mean(dim=1, keepdim=True)
        mx, _ = x.max(dim=1, keepdim=True)
        w = self.sigmoid(self.conv(torch.cat([avg, mx], dim=1)))
        return x * w


class CBAM(nn.Module):
    def __init__(self, channels: int, reduction: int = 16, kernel_size: int = 7):
        super().__init__()
        self.channel_attention = ChannelAttention(channels, reduction)
        self.spatial_attention = SpatialAttention(kernel_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.channel_attention(x)
        x = self.spatial_attention(x)
        return x


class GREGRetina(nn.Module):
    """EfficientNet-B3 + CBAM e cabeça de classificação customizada."""

    def __init__(self, num_classes: int = NUM_CLASSES):
        super().__init__()
        base = efficientnet_b3(weights=None)
        self.backbone = base

        feature_dim = 1536
        self.features = self.backbone.features
        self.cbam = CBAM(channels=feature_dim)

        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(feature_dim, 512),
            nn.ReLU(),
            nn.Dropout(p=0.3),
            nn.Linear(512, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.cbam(x)
        x = self.classifier(x)
        return x


# ─────────────────────────────────────────────
# Pré-processamento
# ─────────────────────────────────────────────
TRANSFORM = T.Compose(
    [
        T.Resize((IMG_SIZE, IMG_SIZE)),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)


def preprocess(image_bytes: bytes) -> torch.Tensor:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = TRANSFORM(img).unsqueeze(0)
    return tensor.to(DEVICE)


def temperature_scale(logits: torch.Tensor, temperature: float = TEMPERATURE) -> torch.Tensor:
    return logits / temperature


# ─────────────────────────────────────────────
# Schemas de resposta
# ─────────────────────────────────────────────


class ClassePredita(BaseModel):
    codigo: int
    descricao: str
    risco: str
    conduta: str


class ResultadoInferencia(BaseModel):
    classe_predita: ClassePredita
    confianca: float
    probabilidades: dict[str, float]
    temperatura_aplicada: float
    tempo_inferencia_ms: float
    dispositivo: str
    modelo_epoca: int
    modelo_val_acc: float


class StatusModelo(BaseModel):
    status: str
    dispositivo: str
    modelo_carregado: bool
    epoca: Optional[int]
    val_acc: Optional[float]
    greg_state: Optional[dict]
    classes: dict


# ─────────────────────────────────────────────
# Estado global do app
# ─────────────────────────────────────────────
app_state: dict = {
    "model": None,
    "epoch": None,
    "val_acc": None,
    "greg_state": None,
}


def _download_from_google_drive(url: str, dest_path: Path, chunk_size: int = 1024 * 1024) -> None:
    """Baixa arquivo do Google Drive (link /view) para dest_path (sem dependências externas)."""
    import urllib.request
    dest_path.parent.mkdir(parents=True, exist_ok=True)


    file_id: Optional[str] = None
    if "/file/d/" in url:
        parts = url.split("/file/d/", 1)
        if len(parts) == 2:
            file_id = parts[1].split("/", 1)[0]

    if not file_id and "id=" in url:
        file_id = url.split("id=", 1)[1].split("&", 1)[0]

    if not file_id:
        raise ValueError("Não foi possível extrair o ID do Google Drive da URL fornecida em GREG_MODEL_DRIVE_URL.")

    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    log.info(f"Baixando checkpoint do Google Drive ({file_id})...")

    # Baixa com urllib (sem requests)
    req = urllib.request.Request(download_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        total = resp.headers.get("content-length")
        total_int = int(total) if total else 0
        downloaded = 0
        with open(dest_path, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total_int:
                    pct = downloaded * 100 / total_int
                    log.info(f"Download: {pct:.1f}%")


    if not dest_path.exists() or dest_path.stat().st_size == 0:
        raise RuntimeError("Download concluído, mas o arquivo ficou inválido (0 bytes).")


def download_model_if_needed() -> None:
    # Importação do módulo não deve provocar download; só chame isso no lifespan.
    if MODEL_PATH.exists():
        return

    log.warning(f"Checkpoint não encontrado em '{MODEL_PATH}'. Iniciando download...")
    _download_from_google_drive(GREG_MODEL_DRIVE_URL, MODEL_PATH)



# ─────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(f"Carregando GREG Retina de '{MODEL_PATH}' no dispositivo '{DEVICE}'...")

    if not MODEL_PATH.exists():
        try:
            download_model_if_needed()
        except Exception as e:
            tentativas = "\n  ".join(str(p) for p in _CHECKPOINT_CANDIDATES if p is not None)
            msg = (
                f"Falha ao obter o checkpoint do modelo. Caminhos tentados:\n  {tentativas}\n\n"
                f"Erro: {e}"
            )
            log.error(msg)
            raise

    checkpoint = torch.load(MODEL_PATH, map_location=DEVICE, weights_only=False)

    model = GREGRetina(num_classes=NUM_CLASSES)

    state = checkpoint["model_state"]
    missing, unexpected = model.load_state_dict(state, strict=False)
    if missing or unexpected:
        log.warning(
            "Estado do checkpoint carregado com diferenças. "
            f"missing={len(missing)} unexpected={len(unexpected)}"
        )

    model.to(DEVICE)
    model.eval()

    app_state["model"] = model
    app_state["epoch"] = checkpoint.get("epoch")
    app_state["val_acc"] = checkpoint.get("val_acc")
    app_state["greg_state"] = checkpoint.get("greg_state")

    log.info(
        f"Modelo carregado ✓  |  época={app_state['epoch']}  "
        f"|  val_acc={app_state['val_acc']:.4f}  |  dispositivo={DEVICE}"
    )
    yield

    app_state["model"] = None
    log.info("Modelo descarregado.")


# ─────────────────────────────────────────────
# App FastAPI
# ─────────────────────────────────────────────
app = FastAPI(
    title="GREG Retina — API de Triagem Oftalmológica",
    description=(
        "Inferência de retinopatia diabética a partir de imagens de fundo de olho. "
        "Modelo: EfficientNet-B3 + CBAM, treinado no APTOS 2019. "
        "Val Acc: 92.08% | 3 classes de severidade."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────


@app.get("/", tags=["Health"])
def raiz():
    return {"servico": "GREG Retina Inference API", "status": "online"}


@app.get("/status", response_model=StatusModelo, tags=["Health"])
def status():
    return StatusModelo(
        status="online" if app_state["model"] is not None else "sem modelo",
        dispositivo=str(DEVICE),
        modelo_carregado=app_state["model"] is not None,
        epoca=app_state["epoch"],
        val_acc=app_state["val_acc"],
        greg_state=app_state["greg_state"],
        classes=CLASSES,
    )


@app.post("/predict", response_model=ResultadoInferencia, tags=["Inferência"])
async def predict(file: UploadFile = File(...)):
    if app_state["model"] is None:
        raise HTTPException(status_code=503, detail="Modelo não carregado.")

    if file.content_type not in ("image/jpeg", "image/png", "image/jpg"):
        raise HTTPException(
            status_code=400,
            detail=f"Formato não suportado: '{file.content_type}'. Use JPEG ou PNG.",
        )

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    try:
        tensor = preprocess(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Erro ao processar imagem: {e}")

    t0 = time.perf_counter()
    with torch.no_grad():
        logits = app_state["model"](tensor)
        logits_scaled = temperature_scale(logits)
        probs = torch.softmax(logits_scaled, dim=1)[0]
    elapsed_ms = (time.perf_counter() - t0) * 1000

    probs_np = probs.cpu().numpy()
    classe_idx = int(np.argmax(probs_np))
    confianca = float(probs_np[classe_idx]) * 100

    probabilidades = {CLASSES[i]: round(float(probs_np[i]) * 100, 2) for i in range(NUM_CLASSES)}

    log.info(
        f"Predição: classe={classe_idx} ({CLASSES[classe_idx]}) | "
        f"confiança={confianca:.1f}% | tempo={elapsed_ms:.1f}ms"
    )

    return ResultadoInferencia(
        classe_predita=ClassePredita(
            codigo=classe_idx,
            descricao=CLASSES[classe_idx],
            risco=RISCO[classe_idx],
            conduta=CONDUTA[classe_idx],
        ),
        confianca=round(confianca, 2),
        probabilidades=probabilidades,
        temperatura_aplicada=TEMPERATURE,
        tempo_inferencia_ms=round(elapsed_ms, 2),
        dispositivo=str(DEVICE),
        modelo_epoca=app_state["epoch"],
        modelo_val_acc=round(app_state["val_acc"] * 100, 4),
    )

