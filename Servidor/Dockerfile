FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY Servidor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY Servidor ./Servidor

EXPOSE 5555
CMD ["python", "-m", "Servidor.main_servidor"]