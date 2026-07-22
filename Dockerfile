FROM python:3.11-slim

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements (where agent code lives)
COPY backend/requirements.txt .

# Install Python dependencies with optimization
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY backend/agents ./agents
COPY backend/config.py .
COPY backend/.env .

EXPOSE 8081

# Run ONLY the agent
CMD ["python", "-m", "agents.agent", "start"]