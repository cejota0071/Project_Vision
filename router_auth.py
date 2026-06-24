from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import Usuario
from backend.schemas.schemas import UsuarioCreate, UsuarioOut, LoginIn, TokenOut
from backend.utils.auth import hash_senha, verificar_senha, criar_token, get_usuario_atual

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/register", response_model=UsuarioOut, status_code=201)
def registrar(body: UsuarioCreate, db: Session = Depends(get_db)):
    if db.query(Usuario).filter(Usuario.email == body.email).first():
        raise HTTPException(400, "E-mail já cadastrado.")
    usuario = Usuario(
        nome       = body.nome,
        email      = body.email,
        senha_hash = hash_senha(body.senha),
        crm        = body.crm,
        clinica    = body.clinica,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == body.email, Usuario.ativo == True).first()
    if not usuario or not verificar_senha(body.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")
    token = criar_token({"sub": usuario.email})
    return TokenOut(access_token=token, usuario=UsuarioOut.model_validate(usuario))


@router.get("/me", response_model=UsuarioOut)
def me(usuario: Usuario = Depends(get_usuario_atual)):
    return usuario