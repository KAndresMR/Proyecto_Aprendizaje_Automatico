# 🚀 GUÍA DE DEPLOYMENT - Servidor para Móvil

Esta guía te muestra cómo subir tu aplicación a un servidor para acceder desde el móvil.

## 📋 Índice

1. [Opciones de Hosting](#opciones-de-hosting)
2. [Deployment en Render (Recomendado - Gratis)](#deployment-en-render)
3. [Deployment en Railway](#deployment-en-railway)
4. [Deployment en VPS (DigitalOcean/AWS)](#deployment-en-vps)
5. [Configuración de HTTPS](#configuración-de-https)
6. [Problemas Comunes](#problemas-comunes)

---

## 🏆 Opciones de Hosting

| Opción | Precio | Pros | Contras | Recomendación |
|--------|--------|------|---------|---------------|
| **Render** | Gratis/5$/mes | Fácil, CI/CD automático, HTTPS gratis | Sleep después de 15min (plan gratis) | ✅ Mejor para empezar |
| **Railway** | Gratis 500h/mes | Muy fácil, PostgreSQL incluido | Requiere tarjeta | ✅ Buena opción |
| **Fly.io** | Gratis (limitado) | Rápido, multi-región | Complejo para principiantes | ⚠️ Avanzado |
| **Heroku** | 7$/mes | Clásico, confiable | Ya no tiene plan gratis | ❌ Costoso |
| **VPS** | 5-20$/mes | Control total | Requiere configuración manual | 🔧 Para expertos |

---

## 🎯 DEPLOYMENT EN RENDER (Recomendado)

### Paso 1: Preparar el Proyecto

#### 1.1 Crear archivo `requirements.txt`

```bash
# En el directorio backend/
pip freeze > requirements.txt
```

Asegúrate de que contenga al menos:

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
asyncpg==0.29.0
psycopg2-binary==2.9.9
python-multipart==0.0.6
pytesseract==0.3.10
easyocr==1.7.0
opencv-python-headless==4.9.0.80
pillow==10.2.0
google-generativeai==0.3.2
sentence-transformers==2.3.1
chromadb==0.4.22
langchain==0.1.6
langchain-community==0.0.20
elevenlabs==0.2.27
```

#### 1.2 Crear `Procfile`

Crear archivo `Procfile` en la raíz del proyecto:

```
web: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

#### 1.3 Crear `render.yaml` (Opcional - IaC)

```yaml
services:
  - type: web
    name: agente-inventario-api
    env: python
    buildCommand: pip install -r backend/requirements.txt
    startCommand: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: inventory-db
          property: connectionString
      - key: GEMINI_API_KEY
        sync: false
      - key: ELEVENLABS_API_KEY
        sync: false
    
  - type: static
    name: agente-inventario-frontend
    buildCommand: ""
    staticPublishPath: ./frontend
    routes:
      - type: rewrite
        source: /*
        destination: /index.html

databases:
  - name: inventory-db
    databaseName: inventory_db
    user: inventory_user
```

### Paso 2: Subir a GitHub

```bash
# Inicializar repositorio si no lo has hecho
git init
git add .
git commit -m "Initial commit - Agente Inventario IA"

# Crear repositorio en GitHub y conectar
git remote add origin https://github.com/tu-usuario/agente-inventario.git
git branch -M main
git push -u origin main
```

### Paso 3: Configurar Render

1. **Ir a** https://render.com y crear cuenta
2. **Click en** "New +" → "Web Service"
3. **Conectar GitHub** → Seleccionar tu repositorio
4. **Configurar:**

```
Name: agente-inventario-api
Environment: Python 3
Build Command: pip install -r backend/requirements.txt
Start Command: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

5. **Agregar variables de entorno:**

```
GEMINI_API_KEY=tu_key_aqui
ELEVENLABS_API_KEY=tu_key_aqui
DATABASE_URL=postgresql://user:pass@host:5432/db
PYTHON_VERSION=3.10.0
```

6. **Click en** "Create Web Service"

### Paso 4: Configurar PostgreSQL en Render

1. **"New +" → "PostgreSQL"**
2. **Configurar:**

```
Name: inventory-db
Database: inventory_db
User: inventory_user
```

3. **Copiar "Internal Database URL"** y pegarla en `DATABASE_URL` del Web Service

4. **Conectarse para crear extensión:**

```bash
# Desde tu máquina local
psql <EXTERNAL_DATABASE_URL>

CREATE EXTENSION IF NOT EXISTS vector;
```

### Paso 5: Configurar Frontend

#### Opción A: Servir desde el mismo backend (Simple)

Modificar `backend/main.py`:

```python
from fastapi.staticfiles import StaticFiles

# Al final del archivo, antes de if __name__ == "__main__":
app.mount("/", StaticFiles(directory="../frontend", html=True), name="static")
```

#### Opción B: Deploy separado en Render (Profesional)

1. **"New +" → "Static Site"**
2. **Seleccionar repositorio**
3. **Configurar:**

```
Publish directory: ./frontend
```

4. **Agregar variable de entorno:**

```
REACT_APP_API_URL=https://agente-inventario-api.onrender.com
```

5. **Actualizar `frontend/app.js`:**

```javascript
// Cambiar la URL del API
const API_URL = import.meta.env.REACT_APP_API_URL || 'http://localhost:8000';
```

### Paso 6: Configurar CORS

En `backend/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tu-frontend.onrender.com",
        "http://localhost:3000",  # Para desarrollo
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Paso 7: Acceder desde Móvil

Tu app estará disponible en:
- API: `https://agente-inventario-api.onrender.com`
- Frontend: `https://agente-inventario-frontend.onrender.com`

**Acceso desde móvil:**
1. Abrir navegador en el teléfono
2. Ir a tu URL de Render
3. La cámara funcionará automáticamente (tu frontend ya es responsive)

---

## 🚂 DEPLOYMENT EN RAILWAY

### Paso 1: Preparar Proyecto

Similar a Render, necesitas `requirements.txt` y `Procfile`.

### Paso 2: Configurar Railway

1. **Ir a** https://railway.app
2. **"New Project" → "Deploy from GitHub repo"**
3. **Seleccionar repositorio**
4. **Agregar PostgreSQL:**
   - Click "New" → "Database" → "Add PostgreSQL"
5. **Configurar variables:**

```
GEMINI_API_KEY=tu_key
ELEVENLABS_API_KEY=tu_key
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

6. **Deploy automático** 🚀

### URL Final

Railway te dará un dominio como:
```
https://tu-app.up.railway.app
```

---

## 💻 DEPLOYMENT EN VPS (DigitalOcean/AWS)

Para usuarios avanzados que quieren control total.

### Paso 1: Crear Droplet/EC2

**DigitalOcean:**
- Plan: $6/mes (1GB RAM)
- OS: Ubuntu 22.04

### Paso 2: Conectar via SSH

```bash
ssh root@tu_ip_publica
```

### Paso 3: Instalar Dependencias

```bash
# Actualizar sistema
apt update && apt upgrade -y

# Instalar Python y PostgreSQL
apt install -y python3 python3-pip postgresql postgresql-contrib nginx

# Instalar Tesseract
apt install -y tesseract-ocr tesseract-ocr-spa

# Instalar Node (para frontend si es necesario)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
apt install -y nodejs
```

### Paso 4: Configurar PostgreSQL

```bash
# Cambiar a usuario postgres
sudo -u postgres psql

# Crear base de datos
CREATE DATABASE inventory_db;
CREATE USER inventory_user WITH PASSWORD 'tu_password_seguro';
GRANT ALL PRIVILEGES ON DATABASE inventory_db TO inventory_user;

# Instalar pgvector
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
make install

# Conectar y crear extensión
sudo -u postgres psql -d inventory_db
CREATE EXTENSION vector;
```

### Paso 5: Clonar y Configurar Proyecto

```bash
# Crear directorio
mkdir /var/www
cd /var/www

# Clonar repositorio
git clone https://github.com/tu-usuario/agente-inventario.git
cd agente-inventario/backend

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Crear .env
nano .env
```

Contenido de `.env`:
```env
DATABASE_URL=postgresql+asyncpg://inventory_user:tu_password@localhost/inventory_db
GEMINI_API_KEY=tu_key
ELEVENLABS_API_KEY=tu_key
```

### Paso 6: Configurar Systemd (Para que el backend corra siempre)

```bash
sudo nano /etc/systemd/system/inventory-api.service
```

Contenido:
```ini
[Unit]
Description=Agente Inventario API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/agente-inventario/backend
Environment="PATH=/var/www/agente-inventario/backend/venv/bin"
ExecStart=/var/www/agente-inventario/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Activar servicio:
```bash
systemctl enable inventory-api
systemctl start inventory-api
systemctl status inventory-api
```

### Paso 7: Configurar Nginx (Reverse Proxy + Frontend)

```bash
sudo nano /etc/nginx/sites-available/inventory
```

Contenido:
```nginx
server {
    listen 80;
    server_name tu_dominio.com;

    # Frontend
    location / {
        root /var/www/agente-inventario/frontend;
        try_files $uri $uri/ /index.html;
    }

    # API
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Uploads
    client_max_body_size 50M;
}
```

Activar configuración:
```bash
ln -s /etc/nginx/sites-available/inventory /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### Paso 8: Configurar HTTPS con Let's Encrypt

```bash
# Instalar Certbot
apt install -y certbot python3-certbot-nginx

# Obtener certificado
certbot --nginx -d tu_dominio.com

# Auto-renovación
certbot renew --dry-run
```

### Paso 9: Acceder desde Móvil

Ahora tu app estará en:
```
https://tu_dominio.com
```

---

## 🔒 CONFIGURACIÓN DE HTTPS

HTTPS es **OBLIGATORIO** para usar la cámara en móvil.

### En Render/Railway
✅ HTTPS viene activado por defecto

### En VPS
Usar Let's Encrypt (ver Paso 8 arriba)

### Verificar HTTPS
```bash
curl -I https://tu-dominio.com
```

Debe responder con `200 OK` y `strict-transport-security` header.

---

## ⚠️ PROBLEMAS COMUNES

### 1. La cámara no funciona en móvil

**Causa:** No estás usando HTTPS

**Solución:**
```javascript
// Verificar en app.js que esté usando HTTPS
if (location.protocol !== 'https:' && location.hostname !== 'localhost') {
    alert('La cámara requiere HTTPS');
}
```

### 2. Error de CORS

**Solución en backend/main.py:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios exactos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. Imágenes muy grandes

**Solución en frontend/app.js:**
```javascript
// Comprimir imagen antes de enviar
canvas.toBlob((blob) => {
    // Reducir tamaño
}, 'image/jpeg', 0.7);  // Calidad 70%
```

### 4. Base de datos no conecta

**Verificar:**
```bash
# En el servidor
psql $DATABASE_URL -c "SELECT 1;"
```

### 5. Frontend no carga el API

**Actualizar URL en app.js:**
```javascript
const API_URL = window.location.origin.includes('localhost') 
    ? 'http://localhost:8000'
    : 'https://tu-api.onrender.com';
```

---

## 📱 VERIFICAR EN MÓVIL

1. **Abrir navegador** (Chrome/Safari)
2. **Ir a tu URL**
3. **Permitir acceso a cámara** cuando lo solicite
4. **Probar captura** de producto

### Debugging en Móvil

**Chrome:**
1. Conectar celular via USB
2. En PC: `chrome://inspect`
3. Ver consola del móvil

**Safari (iOS):**
1. Activar "Web Inspector" en iPhone
2. Conectar a Mac
3. Safari → Develop → iPhone

---

## 🎯 CHECKLIST FINAL

- [ ] Backend corriendo en servidor
- [ ] PostgreSQL con PGVector configurado
- [ ] Frontend accesible via HTTPS
- [ ] Variables de entorno configuradas
- [ ] CORS configurado correctamente
- [ ] Cámara funciona en móvil
- [ ] Imágenes se suben correctamente
- [ ] Base de datos guarda productos
- [ ] Logs visibles para debugging

---

## 📞 SOPORTE

Si tienes problemas:

1. **Revisar logs:**
   ```bash
   # Render
   Ver en dashboard → Logs
   
   # VPS
   journalctl -u inventory-api -f
   ```

2. **Verificar variables de entorno:**
   ```bash
   env | grep DATABASE_URL
   ```

3. **Test de conectividad:**
   ```bash
   curl https://tu-api.com/api/health
   ```

---

## 🚀 PRÓXIMOS PASOS

Una vez desplegado:

1. **Monitoreo:** Configurar Sentry/LogRocket
2. **Analytics:** Google Analytics
3. **CDN:** CloudFlare para imágenes
4. **Backup:** Backup automático de PostgreSQL
5. **CI/CD:** GitHub Actions para deploy automático

---

**¡Listo! Tu aplicación está en producción y accesible desde cualquier móvil 📱**
