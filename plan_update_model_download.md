Plano (sem dependências externas)

1) Reescrever `greg_retina_inference.py` garantindo:
   - `download` do Google Drive via `urllib.request` (sem `requests`).
   - `download` e `torch.load` ocorrem somente dentro do `lifespan`.
   - URL do Drive sempre convertida para `https://drive.google.com/uc?export=download&id=<ID>`.
   - Validação pós-download (tamanho > 0) e logs claros.

2) Garantir compatibilidade com env vars:
   - `GREG_MODEL_PATH` (se definido e existir, não baixa).
   - `GREG_MODEL_DRIVE_URL` (default para o link fornecido).

3) Após reescrita, testar:
   - Subir com `uvicorn greg_retina_inference:app ...`.
   - Chamar `GET /status` e confirmar `modelo_carregado=true`.

