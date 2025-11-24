FROM python:3.10-slim

# Carpeta de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias primero
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install python-multipart

# Copiar solo el codigo necesario
COPY app/ app/
COPY ml/ ml/
COPY models/ models/
COPY data/ data/

EXPOSE 8080

# Comando de arranque
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8080"]