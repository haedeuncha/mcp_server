# 빌드: (서비스 폴더에서) docker build -f docker/Dockerfile .
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONPATH=/app/src PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip && python -m pip install --no-cache-dir -r requirements.txt
COPY src ./src
EXPOSE 8501
CMD ["streamlit", "run", "src/frontend/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
