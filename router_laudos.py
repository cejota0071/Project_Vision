from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import Laudo, Exame, Paciente, Usuario
from backend.schemas.schemas import LaudoCreate, LaudoOut
from backend.utils.auth import get_usuario_atual
from backend.pdf_generator import gerar_pdf

import uuid
from datetime import datetime
from pathlib import Path

from backend.config import settings

router = APIRouter(prefix="/laudos", tags=["Laudos"])


@router.post("/{exame_id}", response_model=LaudoOut)
def gerar_laudo(
    exame_id: int,
    body: LaudoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    exame = db.query(Exame).filter(Exame.id == exame_id, Exame.usuario_id == usuario.id).first()
    if not exame:
        raise HTTPException(404, "Exame não encontrado.")

    paciente = db.query(Paciente).filter(Paciente.id == exame.paciente_id, Paciente.criado_por == usuario.id).first()
    if not paciente:
        raise HTTPException(404, "Paciente não encontrado.")

    # Se já existe laudo para este exame, atualiza
    laudo = db.query(Laudo).filter(Laudo.exame_id == exame_id).first()
    if not laudo:
        laudo = Laudo(exame_id=exame_id)
        db.add(laudo)

    laudo.titulo = body.titulo or laudo.titulo
    laudo.observacoes = body.observacoes
    laudo.assinado_por = body.assinado_por or usuario.nome
    laudo.crm_assinante = body.crm_assinante or usuario.crm

    pdf_path = gerar_pdf(exame=exame, paciente=paciente, usuario=usuario, laudo=laudo)

    laudo.pdf_path = str(pdf_path)
    laudo.gerado_em = datetime.utcnow()

    db.commit()
    db.refresh(laudo)
    return laudo


@router.get("/{laudo_id}/download")
def download_laudo(
    laudo_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    laudo = db.query(Laudo).filter(Laudo.id == laudo_id).first()
    if not laudo:
        raise HTTPException(404, "Laudo não encontrado.")

    # Authorization: exame pertence ao usuário
    exame = db.query(Exame).filter(Exame.id == laudo.exame_id, Exame.usuario_id == usuario.id).first()
    if not exame:
        raise HTTPException(403, "Sem permissão para este laudo.")

    if not laudo.pdf_path:
        raise HTTPException(404, "PDF ainda não gerado.")

    p = Path(laudo.pdf_path)
    if not p.exists():
        raise HTTPException(404, "PDF não encontrado no storage.")

    return FileResponse(path=str(p), filename=p.name, media_type="application/pdf")

