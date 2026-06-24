# TODO

## GREG Retina model download do Google Drive (para deploy)

- [x] Atualizar `greg_retina_inference.py` para baixar automaticamente `best_model.pt` do Google Drive quando não existir no disco.

- [x] Salvar o modelo em `experiments/greg_retina_output_v3/checkpoints/best_model.pt` (mesmo caminho que o carregador atual tenta).

- [x] Permitir override via env vars: `GREG_MODEL_PATH` e `GREG_MODEL_DRIVE_URL`.
- [x] Garantir logs claros e falha amigável se o download não funcionar.
- [ ] Testar localmente: iniciar a API e chamar `GET /status`.


