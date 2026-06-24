from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship
import enum

from backend.database import Base


class RiscoEnum(str, enum.Enum):
    baixo    = "baixo"
    moderado = "moderado"
    alto     = "alto"


class Usuario(Base):
    __tablename__ = "usuarios"

    id           = Column(Integer, primary_key=True, index=True)
    nome         = Column(String(120), nullable=False)
    email        = Column(String(120), unique=True, index=True, nullable=False)
    senha_hash   = Column(String(256), nullable=False)
    crm          = Column(String(30), nullable=True)
    clinica      = Column(String(150), nullable=True)
    is_admin     = Column(Boolean, default=False)
    ativo        = Column(Boolean, default=True)
    criado_em    = Column(DateTime, default=datetime.utcnow)

    pacientes    = relationship("Paciente", back_populates="criado_por_usuario")
    exames       = relationship("Exame",    back_populates="usuario")


class Paciente(Base):
    __tablename__ = "pacientes"

    id               = Column(Integer, primary_key=True, index=True)
    nome             = Column(String(150), nullable=False)
    cpf              = Column(String(14), unique=True, index=True, nullable=True)
    data_nascimento  = Column(String(10), nullable=True)   # DD/MM/AAAA
    telefone         = Column(String(20), nullable=True)
    email            = Column(String(120), nullable=True)
    diabetes_tipo    = Column(String(30), nullable=True)   # Tipo 1, Tipo 2, Gestacional
    observacoes      = Column(Text, nullable=True)
    criado_por       = Column(Integer, ForeignKey("usuarios.id"))
    criado_em        = Column(DateTime, default=datetime.utcnow)

    criado_por_usuario = relationship("Usuario",  back_populates="pacientes")
    exames             = relationship("Exame",    back_populates="paciente",
                                      order_by="Exame.criado_em.desc()")


class Exame(Base):
    __tablename__ = "exames"

    id              = Column(Integer, primary_key=True, index=True)
    paciente_id     = Column(Integer, ForeignKey("pacientes.id"), nullable=False)
    usuario_id      = Column(Integer, ForeignKey("usuarios.id"),  nullable=False)

    # Imagem
    imagem_path     = Column(String(512), nullable=True)
    imagem_filename = Column(String(256), nullable=True)

    # Resultado da inferência
    classe_predita  = Column(Integer, nullable=False)          # 0, 1, 2
    descricao       = Column(String(100), nullable=False)
    risco           = Column(SAEnum(RiscoEnum), nullable=False)
    conduta         = Column(Text, nullable=False)
    prob_0          = Column(Float, nullable=False)            # Sem retinopatia
    prob_1          = Column(Float, nullable=False)            # Leve/Moderada
    prob_2          = Column(Float, nullable=False)            # Grave/Proliferativa
    confianca       = Column(Float, nullable=False)
    tempo_ms        = Column(Float, nullable=True)
    dispositivo     = Column(String(30), nullable=True)
    temperatura     = Column(Float, default=1.50)

    # Anotações clínicas (editáveis pelo médico)
    observacoes_medico  = Column(Text, nullable=True)
    confirmado_medico   = Column(Boolean, default=False)

    criado_em       = Column(DateTime, default=datetime.utcnow)

    paciente  = relationship("Paciente", back_populates="exames")
    usuario   = relationship("Usuario",  back_populates="exames")
    laudo     = relationship("Laudo",    back_populates="exame", uselist=False)


class Laudo(Base):
    __tablename__ = "laudos"

    id              = Column(Integer, primary_key=True, index=True)
    exame_id        = Column(Integer, ForeignKey("exames.id"), unique=True, nullable=False)

    # Dados editáveis antes de gerar o PDF
    titulo          = Column(String(200), default="Laudo de Triagem — Retinopatia Diabética")
    observacoes     = Column(Text, nullable=True)
    assinado_por    = Column(String(150), nullable=True)   # nome do médico no laudo
    crm_assinante   = Column(String(30),  nullable=True)

    pdf_path        = Column(String(512), nullable=True)
    gerado_em       = Column(DateTime, nullable=True)
    criado_em       = Column(DateTime, default=datetime.utcnow)

    exame = relationship("Exame", back_populates="laudo")