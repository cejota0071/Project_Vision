"""
Gerador de laudo clínico em PDF usando WeasyPrint.
O HTML do laudo é gerado internamente — editável via campos do Laudo.
"""
from datetime import datetime
from pathlib import Path
import base64

from backend.config import settings


RISCO_COR = {
    "baixo":    ("#3A7A5C", "#E8F5EE"),
    "moderado": ("#D4883A", "#FDF3E8"),
    "alto":     ("#C8563A", "#FDEEE8"),
}

PROB_LABELS = [
    "Sem Retinopatia Diabética",
    "Retinopatia Leve / Moderada",
    "Retinopatia Grave / Proliferativa",
]


def _barra_html(label: str, pct: float, cor: str) -> str:
    return f"""
    <div class="prob-item">
      <div class="prob-header">
        <span>{label}</span>
        <strong>{pct:.1f}%</strong>
      </div>
      <div class="prob-track">
        <div class="prob-fill" style="width:{pct}%;background:{cor}"></div>
      </div>
    </div>"""


def gerar_html_laudo(exame, paciente, usuario, laudo) -> str:
    risco        = exame.risco.value if hasattr(exame.risco, 'value') else exame.risco
    cor_txt, cor_bg = RISCO_COR.get(risco, ("#555", "#F5F5F5"))

    probs = [exame.prob_0 * 100, exame.prob_1 * 100, exame.prob_2 * 100]
    cor_barras = ["#3A7A5C", "#D4883A", "#C8563A"]

    barras_html = "".join(
        _barra_html(PROB_LABELS[i], probs[i], cor_barras[i])
        for i in range(3)
    )

    # Imagem do exame em base64 (se existir)
    img_tag = ""
    if exame.imagem_path and Path(exame.imagem_path).exists():
        img_bytes = Path(exame.imagem_path).read_bytes()
        img_b64   = base64.b64encode(img_bytes).decode()
        img_tag   = f'<img class="retina-img" src="data:image/jpeg;base64,{img_b64}" alt="Imagem retinal" />'

    assinante = laudo.assinado_por or usuario.nome
    crm_str   = f"CRM: {laudo.crm_assinante or usuario.crm or '—'}"
    obs_medico = exame.observacoes_medico or "—"
    obs_laudo  = laudo.observacoes or ""
    data_exame = exame.criado_em.strftime("%d/%m/%Y às %H:%M")
    data_laudo = datetime.utcnow().strftime("%d/%m/%Y")
    confirmado = "✓ Confirmado pelo médico" if exame.confirmado_medico else "⚠ Aguardando confirmação médica"

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"/>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600&family=DM+Sans:wght@300;400;500&display=swap');
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{
    font-family:'DM Sans',sans-serif; font-size:11pt;
    color:#1A1916; background:#fff;
    padding:2cm 2.2cm;
  }}
  /* Cabeçalho */
  .header {{ display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:2rem; padding-bottom:1rem; border-bottom:2px solid #1A5C6B; }}
  .logo {{ font-family:'Cormorant Garamond',serif; font-size:22pt; font-weight:600; color:#1A5C6B; }}
  .logo span {{ font-style:italic; color:#4A8FA0; }}
  .header-meta {{ text-align:right; font-size:8.5pt; color:#6B6760; line-height:1.7; }}
  /* Título */
  h1 {{ font-family:'Cormorant Garamond',serif; font-size:16pt; font-weight:600; color:#1A1916; margin-bottom:.25rem; }}
  .subtitle {{ font-size:9pt; color:#6B6760; margin-bottom:2rem; }}
  /* Seções */
  .section {{ margin-bottom:1.5rem; }}
  .section-title {{ font-size:8pt; font-weight:500; letter-spacing:.1em; text-transform:uppercase; color:#6B6760; margin-bottom:.6rem; padding-bottom:.3rem; border-bottom:1px solid #E8E4DC; }}
  /* Grid dados */
  .grid-2 {{ display:grid; grid-template-columns:1fr 1fr; gap:.4rem 2rem; }}
  .grid-3 {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:.4rem 1.5rem; }}
  .field {{ display:flex; flex-direction:column; gap:.1rem; }}
  .field label {{ font-size:7.5pt; color:#B0ABA0; letter-spacing:.06em; text-transform:uppercase; }}
  .field span  {{ font-size:10pt; color:#1A1916; }}
  /* Resultado */
  .resultado-card {{ padding:1rem 1.2rem; border-radius:8px; border-left:4px solid {cor_txt}; background:{cor_bg}; margin-bottom:1.2rem; }}
  .risco-label {{ font-size:7.5pt; font-weight:500; letter-spacing:.1em; text-transform:uppercase; color:{cor_txt}; margin-bottom:.25rem; }}
  .classe-nome {{ font-family:'Cormorant Garamond',serif; font-size:15pt; font-weight:600; margin-bottom:.4rem; }}
  .conduta {{ font-size:9.5pt; color:#6B6760; line-height:1.5; }}
  /* Probabilidades */
  .prob-item {{ margin-bottom:.6rem; }}
  .prob-header {{ display:flex; justify-content:space-between; font-size:9pt; margin-bottom:.25rem; }}
  .prob-track {{ height:6px; background:#E8E4DC; border-radius:3px; overflow:hidden; }}
  .prob-fill  {{ height:100%; border-radius:3px; }}
  /* Imagem */
  .retina-img {{ max-width:220px; max-height:220px; border-radius:8px; border:1px solid #E8E4DC; display:block; margin:0 auto; }}
  /* Layout imagem + resultado */
  .result-layout {{ display:grid; grid-template-columns:240px 1fr; gap:1.5rem; align-items:start; }}
  /* Observações */
  .obs-box {{ background:#F2F0EC; border-radius:6px; padding:.8rem 1rem; font-size:9.5pt; line-height:1.6; color:#3A3835; min-height:3rem; }}
  /* Confirmação */
  .confirmacao {{ font-size:8.5pt; color:#6B6760; font-style:italic; margin-top:.5rem; }}
  /* Meta inferência */
  .meta-chips {{ display:flex; gap:.75rem; flex-wrap:wrap; margin-top:.5rem; }}
  .chip {{ font-size:7.5pt; padding:.2rem .6rem; border-radius:20px; background:#E8E4DC; color:#6B6760; font-family:monospace; }}
  /* Assinatura */
  .assinatura {{ margin-top:2.5rem; padding-top:1.5rem; border-top:1px solid #E8E4DC; display:flex; justify-content:space-between; align-items:flex-end; }}
  .ass-linha {{ text-align:center; }}
  .ass-linha .linha {{ width:200px; border-bottom:1px solid #1A1916; margin-bottom:.3rem; }}
  .ass-nome {{ font-size:9.5pt; font-weight:500; }}
  .ass-sub  {{ font-size:8pt; color:#6B6760; }}
  /* Rodapé */
  .footer {{ margin-top:1.5rem; padding-top:.75rem; border-top:1px solid #E8E4DC; font-size:7.5pt; color:#B0ABA0; text-align:center; line-height:1.6; }}
  .aviso {{ background:#FFF8E8; border:1px solid #E8C882; border-radius:6px; padding:.6rem 1rem; font-size:8.5pt; color:#6B5000; margin-top:1rem; }}
</style>
</head>
<body>

<div class="header">
  <div class="logo">GREG <span>Retinopatia</span></div>
  <div class="header-meta">
    Data do laudo: {data_laudo}<br/>
    Exame ID: #{exame.id}<br/>
    Laudo ID: #{laudo.id}
  </div>
</div>

<h1>{laudo.titulo}</h1>
<div class="subtitle">Triagem automatizada por rede neural — EfficientNet-B3 + CBAM · APTOS 2019 · Acurácia: 92.08%</div>

<!-- DADOS DO PACIENTE -->
<div class="section">
  <div class="section-title">Dados do Paciente</div>
  <div class="grid-2">
    <div class="field"><label>Nome</label><span>{paciente.nome}</span></div>
    <div class="field"><label>CPF</label><span>{paciente.cpf or '—'}</span></div>
    <div class="field"><label>Data de Nascimento</label><span>{paciente.data_nascimento or '—'}</span></div>
    <div class="field"><label>Tipo de Diabetes</label><span>{paciente.diabetes_tipo or '—'}</span></div>
    <div class="field"><label>Telefone</label><span>{paciente.telefone or '—'}</span></div>
    <div class="field"><label>Data do Exame</label><span>{data_exame}</span></div>
  </div>
</div>

<!-- RESULTADO -->
<div class="section">
  <div class="section-title">Resultado da Análise</div>
  <div class="result-layout">
    <div>
      {img_tag or '<div style="width:220px;height:180px;background:#F2F0EC;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:8pt;color:#B0ABA0">Imagem não disponível</div>'}
    </div>
    <div>
      <div class="resultado-card">
        <div class="risco-label">RISCO {risco.upper()}</div>
        <div class="classe-nome">{exame.descricao}</div>
        <div class="conduta">{exame.conduta}</div>
      </div>
      <div class="section-title" style="margin-top:.75rem">Distribuição de Probabilidades</div>
      {barras_html}
      <div class="meta-chips">
        <span class="chip">Confiança: {exame.confianca:.1f}%</span>
        <span class="chip">T={exame.temperatura:.2f}</span>
        <span class="chip">{exame.dispositivo or 'CPU'}</span>
        <span class="chip">{exame.tempo_ms:.0f}ms</span>
      </div>
    </div>
  </div>
</div>

<!-- OBSERVAÇÕES MÉDICAS -->
<div class="section">
  <div class="section-title">Observações do Médico</div>
  <div class="obs-box">{obs_medico}</div>
  <div class="confirmacao">{confirmado}</div>
</div>

{'<div class="section"><div class="section-title">Notas Adicionais</div><div class="obs-box">' + obs_laudo + '</div></div>' if obs_laudo else ''}

<div class="aviso">
  ⚠ Este laudo é gerado por sistema de apoio ao diagnóstico baseado em inteligência artificial.
  Não substitui a avaliação clínica por profissional habilitado. Resultado deve ser interpretado
  por médico oftalmologista ou clínico geral com experiência em retinopatia diabética.
</div>

<!-- ASSINATURA -->
<div class="assinatura">
  <div class="ass-linha">
    <div class="linha"></div>
    <div class="ass-nome">{assinante}</div>
    <div class="ass-sub">{crm_str}</div>
    <div class="ass-sub">{laudo.clinica if hasattr(laudo, 'clinica') else usuario.clinica or ''}</div>
  </div>
  <div style="text-align:right;font-size:8pt;color:#B0ABA0">
    Uberlândia, {data_laudo}<br/>
    gregretinopatia.com.br
  </div>
</div>

<div class="footer">
  GREG Retinopatia · Sistema de Triagem Oftalmológica com IA · Uberlândia — MG<br/>
  Desenvolvido com base no dataset APTOS 2019 · Uso restrito a fins de triagem em atenção primária
</div>

</body>
</html>"""


def gerar_pdf(exame, paciente, usuario, laudo) -> Path:
    """Gera o PDF do laudo e retorna o path do arquivo."""
    try:
        from weasyprint import HTML
    except ImportError:
        raise RuntimeError("WeasyPrint não instalado. Execute: pip install weasyprint")

    html_str  = gerar_html_laudo(exame, paciente, usuario, laudo)
    filename  = f"laudo_{laudo.id}_exame_{exame.id}.pdf"
    pdf_path  = settings.PDF_DIR / filename

    HTML(string=html_str).write_pdf(str(pdf_path))
    return pdf_path