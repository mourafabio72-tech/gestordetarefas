# Gestor de Tarefas

Sistema de gestão de tarefas para empresas de contabilidade.

## Funcionalidades

- Dashboard com visão geral de tarefas
- Cadastro de empresas/clientes
- Cadastro de setores
- Gestão de usuários
- Controle de tarefas com prazos
- Alertas de vencimento
- Filtros por empresa e status

## Stack

- **Backend**: FastAPI + PostgreSQL
- **Frontend**: React + Tailwind CSS
- **Deploy**: Docker + EasyPanel

## Pré-requisitos

- Docker e Docker Compose
- Node.js 18+ (para desenvolvimento local)
- Python 3.11+ (para desenvolvimento local)

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/gestor-de-tarefas.git
cd gestor-de-tarefas
```

2. Copie o arquivo de exemplo de variáveis de ambiente:
```bash
cp .env.example .env
```

3. Edite o arquivo `.env` com suas configurações:
```env
DB_USER=postgres
DB_PASSWORD=sua_senha_segura
SECRET_KEY=sua_chave_secreta_muito_segura
```

4. Execute com Docker Compose:
```bash
docker-compose up -d
```

5. Acesse:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Documentação API: http://localhost:8000/docs

## Desenvolvimento Local

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Estrutura do Projeto

```
gestor-de-tarefas/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── database.py
│   │   ├── auth.py
│   │   └── routes/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── contexts/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Deploy no EasyPanel

1. Suba o código no GitHub
2. No EasyPanel, crie um novo projeto
3. Conecte o repositório GitHub
4. Configure as variáveis de ambiente
5. Faça o deploy

## Licença

MIT