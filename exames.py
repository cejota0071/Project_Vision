import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import Exame, Paciente, Usuario
from backend.schemas.schemas import ExameOut, ExameUpdate, DashboardOut
from backend.utils.auth import get_usuario_atual
from backend.services.inference import chamar_inferencia, status_inferencia
from backend.config import settings

router = APIRouter(prefix="/exames", tags=["Exames"])


@router.post("", response_model=ExameOut, status_code=201)
async def criar_exame(
    paciente_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Recebe imagem, chama inferência, salva resultado no banco."""

    # Verifica paciente
    paciente = db.query(Paciente).filter(
        Paciente.id == paciente_id,
        Paciente.criado_por == usuario.id,
    ).first()
    if not paciente:
        raise HTTPException(404, "Paciente não encontrado.")

    # Valida imagem
    if file.content_type not in ("image/jpeg", "image/png", "image/jpg"):
        raise HTTPException(400, "Apenas JPEG ou PNG são aceitos.")

    imagem_bytes = await file.read()
    if len(imagem_bytes) == 0:
        raise HTTPException(400, "Arquivo vazio.")

    # Salva imagem em disco
    ext      = Path(file.filename).suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    img_path = settings.UPLOAD_DIR / filename
    img_path.write_bytes(imagem_bytes)

    # Chama inferência
    resultado = await chamar_inferencia(imagem_bytes, file.filename)

    cp   = resultado["classe_predita"]
    probs = resultado["probabilidades"]
    class_names = [
        "Sem Retinopatia Diabética",
        "Retinopatia Leve / Moderada",
        "Retinopatia Grave / Proliferativa",
    ]

    exame = Exame(
        paciente_id     = paciente_id,
        usuario_id      = usuario.id,
        imagem_path     = str(img_path),
        imagem_filename = file.filename,
        classe_predita  = cp["codigo"],
        descricao       = cp["descricao"],
        risco           = cp["risco"],
        conduta         = cp["conduta"],
        prob_0          = probs.get(class_names[0], 0) / 100,
        prob_1          = probs.get(class_names[1], 0) / 100,
        prob_2          = probs.get(class_names[2], 0) / 100,
        confianca       = resultado["confianca"],
        tempo_ms        = resultado.get("tempo_inferencia_ms"),
        dispositivo     = resultado.get("dispositivo"),
        temperatura     = resultado.get("temperatura_aplicada", 1.50),
    )
    db.add(exame)
    db.commit()
    db.refresh(exame)
    return exame


@router.get("/paciente/{paciente_id}", response_model=List[ExameOut])
def historico_paciente(
    paciente_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    paciente = db.query(Paciente).filter(
        Paciente.id == paciente_id,
        Paciente.criado_por == usuario.id,
    ).first()
    if not paciente:
        raise HTTPException(404, "Paciente não encontrado.")
    return paciente.exames


@router.get("/{exame_id}", response_model=ExameOut)
def detalhe(
    exame_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    exame = db.query(Exame).filter(
        Exame.id == exame_id,
        Exame.usuario_id == usuario.id,
    ).first()
    if not exame:
        raise HTTPException(404, "Exame não encontrado.")
    return exame


@router.patch("/{exame_id}", response_model=ExameOut)
def atualizar_exame(
    exame_id: int,
    body: ExameUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Médico pode adicionar observações e confirmar o diagnóstico."""
    exame = db.query(Exame).filter(
        Exame.id == exame_id,
        Exame.usuario_id == usuario.id,
    ).first()
    if not exame:
        raise HTTPException(404, "Exame não encontrado.")
    for campo, valor in body.model_dump(exclude_none=True).items():
        setattr(exame, campo, valor)
    db.commit()
    db.refresh(exame)
    return exame


@router.get("/inference/status")
async def inference_status():
    return await status_inferencia()


@router.get("/dashboard/resumo", response_model=DashboardOut)
def dashboard(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    from backend.models.models import Laudo
    from sqlalchemy import func

    total_pac   = db.query(Paciente).filter(Paciente.criado_por == usuario.id).count()
    total_exam  = db.query(Exame).filter(Exame.usuario_id == usuario.id).count()
    sem_risco   = db.query(Exame).filter(Exame.usuario_id == usuario.id, Exame.risco == "baixo").count()
    moderado    = db.query(Exame).filter(Exame.usuario_id == usuario.id, Exame.risco == "moderado").count()
    alto        = db.query(Exame).filter(Exame.usuario_id == usuario.id, Exame.risco == "alto").count()
    laudos      = db.query(Laudo).join(Exame).filter(Exame.usuario_id == usuario.id).count()
    ultimo      = db.query(func.max(Exame.criado_em)).filter(Exame.usuario_id == usuario.id).scalar()

    return DashboardOut(
        total_pacientes  = total_pac,
        total_exames     = total_exam,
        exames_sem_risco = sem_risco,
        exames_moderado  = moderado,
        exames_alto      = alto,
        laudos_gerados   = laudos,
        ultimo_exame     = ultimo,
    )