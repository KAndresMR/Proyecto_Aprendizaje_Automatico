FROM python:3.10

# Carpeta de trabajo dentro del contenedor
WORKDIR /app

# Copiar dependencias primero (mejora cache de Docker)
COPY . .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Exponer puerto de Cloud Run
EXPOSE 8080

# Comando de arranque
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8080"]