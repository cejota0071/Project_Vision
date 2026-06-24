from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import Paciente, Usuario
from backend.schemas.schemas import PacienteCreate, PacienteUpdate, PacienteOut
from backend.utils.auth import get_usuario_atual

router = APIRouter(prefix="/pacientes", tags=["Pacientes"])


@router.get("", response_model=List[PacienteOut])
def listar(
    busca: Optional[str] = Query(None, description="Busca por nome ou CPF"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    q = db.query(Paciente).filter(Paciente.criado_por == usuario.id)
    if busca:
        q = q.filter(
            Paciente.nome.ilike(f"%{busca}%") |
            Paciente.cpf.ilike(f"%{busca}%")
        )
    pacientes = q.order_by(Paciente.nome).offset(skip).limit(limit).all()

    result = []
    for p in pacientes:
        out = PacienteOut.model_validate(p)
        out.total_exames = len(p.exames)
        result.append(out)
    return result


@router.post("", response_model=PacienteOut, status_code=201)
def criar(
    body: PacienteCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    if body.cpf:
        existe = db.query(Paciente).filter(Paciente.cpf == body.cpf).first()
        if existe:
            raise HTTPException(400, f"CPF já cadastrado (paciente ID {existe.id}).")
    p = Paciente(**body.model_dump(), criado_por=usuario.id)
    db.add(p)
    db.commit()
    db.refresh(p)
    out = PacienteOut.model_validate(p)
    out.total_exames = 0
    return out


@router.get("/{paciente_id}", response_model=PacienteOut)
def detalhe(
    paciente_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    p = db.query(Paciente).filter(
        Paciente.id == paciente_id,
        Paciente.criado_por == usuario.id,
    ).first()
    if not p:
        raise HTTPException(404, "Paciente não encontrado.")
    out = PacienteOut.model_validate(p)
    out.total_exames = len(p.exames)
    return out


@router.patch("/{paciente_id}", response_model=PacienteOut)
def atualizar(
    paciente_id: int,
    body: PacienteUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    p = db.query(Paciente).filter(
        Paciente.id == paciente_id,
        Paciente.criado_por == usuario.id,
    ).first()
    if not p:
        raise HTTPException(404, "Paciente não encontrado.")
    for campo, valor in body.model_dump(exclude_none=True).items():
        setattr(p, campo, valor)
    db.commit()
    db.refresh(p)
    out = PacienteOut.model_validate(p)
    out.total_exames = len(p.exames)
    return out


@router.delete("/{paciente_id}", status_code=204)
def deletar(
    paciente_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    p = db.query(Paciente).filter(
        Paciente.id == paciente_id,
        Paciente.criado_por == usuario.id,
    ).first()
    if not p:
        raise HTTPException(404, "Paciente não encontrado.")
    db.delete(p)
    db.commit()