from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator


# ── AUTH ────────────────────────────────────────────────────

class UsuarioCreate(BaseModel):
    nome:    str
    email:   EmailStr
    senha:   str
    crm:     Optional[str] = None
    clinica: Optional[str] = None

class UsuarioOut(BaseModel):
    id:       int
    nome:     str
    email:    str
    crm:      Optional[str]
    clinica:  Optional[str]
    is_admin: bool
    criado_em: datetime
    model_config = {"from_attributes": True}

class LoginIn(BaseModel):
    email: EmailStr
    senha: str

class TokenOut(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    usuario:      UsuarioOut


# ── PACIENTE ────────────────────────────────────────────────

class PacienteCreate(BaseModel):
    nome:            str
    cpf:             Optional[str] = None
    data_nascimento: Optional[str] = None
    telefone:        Optional[str] = None
    email:           Optional[str] = None
    diabetes_tipo:   Optional[str] = None
    observacoes:     Optional[str] = None

class PacienteUpdate(BaseModel):
    nome:            Optional[str] = None
    telefone:        Optional[str] = None
    email:           Optional[str] = None
    diabetes_tipo:   Optional[str] = None
    observacoes:     Optional[str] = None

class PacienteOut(BaseModel):
    id:              int
    nome:            str
    cpf:             Optional[str]
    data_nascimento: Optional[str]
    telefone:        Optional[str]
    email:           Optional[str]
    diabetes_tipo:   Optional[str]
    observacoes:     Optional[str]
    criado_em:       datetime
    total_exames:    Optional[int] = 0
    model_config = {"from_attributes": True}


# ── EXAME ───────────────────────────────────────────────────

class ExameOut(BaseModel):
    id:                  int
    paciente_id:         int
    usuario_id:          int
    imagem_filename:     Optional[str]
    classe_predita:      int
    descricao:           str
    risco:               str
    conduta:             str
    prob_0:              float
    prob_1:              float
    prob_2:              float
    confianca:           float
    tempo_ms:            Optional[float]
    dispositivo:         Optional[str]
    temperatura:         float
    observacoes_medico:  Optional[str]
    confirmado_medico:   bool
    criado_em:           datetime
    model_config = {"from_attributes": True}

class ExameUpdate(BaseModel):
    observacoes_medico: Optional[str] = None
    confirmado_medico:  Optional[bool] = None


# ── LAUDO ───────────────────────────────────────────────────

class LaudoCreate(BaseModel):
    titulo:         Optional[str] = "Laudo de Triagem — Retinopatia Diabética"
    observacoes:    Optional[str] = None
    assinado_por:   Optional[str] = None
    crm_assinante:  Optional[str] = None

class LaudoOut(BaseModel):
    id:             int
    exame_id:       int
    titulo:         str
    observacoes:    Optional[str]
    assinado_por:   Optional[str]
    crm_assinante:  Optional[str]
    pdf_path:       Optional[str]
    gerado_em:      Optional[datetime]
    criado_em:      datetime
    model_config = {"from_attributes": True}


# ── DASHBOARD ───────────────────────────────────────────────

class DashboardOut(BaseModel):
    total_pacientes:    int
    total_exames:       int
    exames_sem_risco:   int
    exames_moderado:    int
    exames_alto:        int
    laudos_gerados:     int
    ultimo_exame:       Optional[datetime]