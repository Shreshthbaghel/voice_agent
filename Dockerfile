FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc g++ make libssl-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements-agent.txt .

RUN pip install --no-cache-dir -r requirements-agent.txt

COPY backend/agents ./agents
COPY backend/config.py ./
COPY backend/models.py ./
COPY backend/database.py ./

EXPOSE 8081

CMD ["python", "-m", "agents.agent", "start"]