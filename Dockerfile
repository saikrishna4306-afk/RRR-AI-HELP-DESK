# One container: FastAPI serves the API and the prebuilt frontend/dist on $PORT (default 8000)
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend backend
COPY data data
COPY frontend/dist frontend/dist
COPY scripts scripts
COPY eval eval
COPY .env.example .env.example
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
