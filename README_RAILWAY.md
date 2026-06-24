# Railway Deploy — Triagem Oftalmológica (GREG Retina)

## Variáveis de ambiente obrigatórias
Crie `.env` (ou configure diretamente no Railway):
- `DATABASE_URL` (PostgreSQL SQLAlchemy)
- `SECRET_KEY` (JWT)

## Rotas
- `GET /` (frontend)
- `GET /login.html`
- `POST /auth/login` (JWT)
- `GET /status` e `POST /predict` (proxies do servidor de inferência já embutido)

## Build / Run
O Dockerfile sobe o serviço no `:8000`.

## Observação
O serviço chama o motor de inferência interno via `greg_retina_inference` e serve `/predict` e `/status`.

