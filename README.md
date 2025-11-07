# Nexa Call Backend

Real-time communication system backend built with FastAPI.

## Features

- Call management (start/end calls)
- User presence tracking
- WebRTC signaling
- JWT authentication
- Rate limiting
- PostgreSQL database
- Docker support

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables in `.env`
4. Run database migrations: `alembic upgrade head`
5. Start the server: `uvicorn app.main:app --reload`

## Docker Setup

```bash
docker-compose up --build