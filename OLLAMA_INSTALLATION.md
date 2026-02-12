# 🚀 Instalación de Llama con Ollama - Paso a Paso

## 📋 Requisitos Previos

### Hardware Mínimo
```
CPU: 4 cores
RAM: 8 GB
Disco: 10 GB libres
GPU: Opcional (recomendado NVIDIA)
```

### Software
```
Python: 3.9+
pip: Actualizado
Sistema: Windows, Mac, o Linux
```

---

## 1️⃣ Instalar Ollama

### 🐧 Linux / Mac
```bash
# Un solo comando
curl -fsSL https://ollama.com/install.sh | sh

# Verificar instalación
ollama --version
```

### 🪟 Windows
```
1. Descargar de: https://ollama.com/download/windows
2. Ejecutar instalador OllamaSetup.exe
3. Seguir el wizard
4. Verificar en CMD: ollama --version
```

### ✅ Verificación
```bash
# Debe mostrar algo como: "ollama version 0.1.xx"
ollama --version

# Debe responder: "Ollama is running"
curl http://localhost:11434
```

---

## 2️⃣ Descargar Modelo Llama

### Opción A: Llama 3.2 (Recomendado para empezar)

```bash
# Ligero y rápido (1 billion params)
ollama pull llama3.2:1b
# Tamaño: ~1.3 GB
# Tiempo: 2-5 min
# RAM: 4 GB

# Balance (3 billion params) ⭐ RECOMENDADO
ollama pull llama3.2:3b
# Tamaño: ~2 GB
# Tiempo: 5-10 min
# RAM: 6 GB
```

### Opción B: Llama 3.1 (Más preciso)

```bash
# Preciso (8 billion params)
ollama pull llama3.1:8b
# Tamaño: ~4.7 GB
# Tiempo: 10-20 min
# RAM: 8 GB

# Muy preciso (70 billion params) - Requiere GPU potente
ollama pull llama3.1:70b
# Tamaño: ~40 GB
# Tiempo: 1-2 horas
# RAM: 32 GB + GPU 24GB
```

### ✅ Verificar Modelos Descargados
```bash
ollama list

# Output ejemplo:
# NAME              SIZE    MODIFIED
# llama3.2:3b       2.0 GB  2 hours ago
# llama3.1:8b       4.7 GB  1 day ago
```

---

## 3️⃣ Probar Ollama

### Test Básico
```bash
# Iniciar chat interactivo
ollama run llama3.2:3b

# Ejemplo de conversación:
# >>> ¿Cuál es la capital de Perú?
# La capital de Perú es Lima.
# 
# >>> /bye
```

### Test con API
```bash
# Request simple
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:3b",
  "prompt": "¿Qué es Python?"
}'

# Debe responder con JSON
```

---

## 4️⃣ Instalar Dependencias Python

```bash
# Crear entorno virtual (recomendado)
python -m venv venv

# Activar
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Instalar LangChain + Ollama
pip install langchain-ollama

# O instalar todas las dependencias
pip install -r requirements.txt
```

---

## 5️⃣ Configurar tu Proyecto

### Actualizar `.env`
```env
# Estrategia por defecto
DEFAULT_AI_STRATEGY=llama

# Modelo Llama
LLAMA_MODEL=llama3.2:3b
LLAMA_BASE_URL=http://localhost:11434
```

### Actualizar `config.py`
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... otros campos ...
    
    # Llama
    LLAMA_MODEL: str = "llama3.2:3b"
    LLAMA_BASE_URL: str = "http://localhost:11434"
    
    class Config:
        env_file = ".env"
```

---

## 6️⃣ Probar LlamaClient

### Crear archivo de prueba
```python
# test_llama.py
from backend.app.services.ai.llama_client import llama_client

# Texto de prueba
ocr_text = """
LECHE GLORIA
ENTERA
Contenido neto: 1000 ml
Precio: S/ 5.50
Lote: L20250212
Vence: 15/06/2025
"""

# Extraer
try:
    result = llama_client.extract(ocr_text)
    
    print("✅ Extracción exitosa:")
    print(f"Nombre: {result['name']}")
    print(f"Marca: {result['brand']}")
    print(f"Tamaño: {result['size']}")
    print(f"Precio: {result['price']}")
    
except Exception as e:
    print(f"❌ Error: {e}")
```

### Ejecutar prueba
```bash
python test_llama.py

# Output esperado:
# ✅ Extracción exitosa:
# Nombre: Leche Gloria Entera
# Marca: Gloria
# Tamaño: 1000ml
# Precio: 5.5
```

---

## 7️⃣ Integrar con tu Endpoint

```python
# En tu endpoint /inventory/from-images
from backend.app.services.ai.ai_extractor_service import ai_extractor_service

@router.post("/inventory/from-images")
async def process_product_images(...):
    # ... tu código de OCR ...
    
    # Usar Llama
    product_info = await asyncio.to_thread(
        ai_extractor_service.extract_product_info,
        ocr_data,
        strategy="llama"  # 👈 Aquí
    )
    
    # ... resto del código ...
```

---

## 🐛 Solución de Problemas

### Error: "Ollama is not running"
```bash
# Solución 1: Iniciar Ollama manualmente
ollama serve

# Solución 2 (Linux): Habilitar servicio
sudo systemctl enable ollama
sudo systemctl start ollama

# Solución 3 (Windows): Reiniciar servicio
# Buscar "Ollama" en Servicios de Windows
```

### Error: "Model not found"
```bash
# Listar modelos
ollama list

# Si no aparece, descargar
ollama pull llama3.2:3b

# Verificar descarga
ollama list
```

### Error: "Timeout" o muy lento
```bash
# Problema: Sin GPU o poca RAM

# Solución 1: Usar modelo más pequeño
ollama pull llama3.2:1b

# Solución 2: Aumentar timeout
# En llama_client.py:
# LlamaClient(timeout=120)  # 2 minutos

# Solución 3: Cerrar otras apps
# Liberar RAM para Ollama
```

### Error: "Port 11434 already in use"
```bash
# Ver qué está usando el puerto
# Linux/Mac:
lsof -i :11434
# Windows:
netstat -ano | findstr :11434

# Matar el proceso
# Linux/Mac:
kill -9 [PID]
# Windows:
taskkill /PID [PID] /F

# Reiniciar Ollama
ollama serve
```

### Llama da resultados pobres
```bash
# Solución 1: Usar modelo más grande
ollama pull llama3.1:8b

# Solución 2: Ajustar temperatura
# En llama_client.py:
# OllamaLLM(temperature=0.1)  # Más conservador

# Solución 3: Mejorar el prompt
# Editar _create_prompt_template() en llama_client.py
```

---

## 🔧 Configuración Avanzada

### GPU (NVIDIA)
```bash
# Verificar que Ollama detecta GPU
ollama run llama3.2:3b --verbose

# Debe mostrar:
# "Using GPU: NVIDIA GeForce RTX..."

# Si no detecta:
# 1. Instalar drivers NVIDIA
# 2. Instalar CUDA toolkit
# 3. Reiniciar Ollama
```

### Múltiples Modelos
```python
# Puedes tener varios modelos
from backend.app.services.ai.llama_client import LlamaClient

# Cliente rápido
fast_client = LlamaClient(model="llama3.2:1b")

# Cliente preciso
accurate_client = LlamaClient(model="llama3.1:8b")

# Usar según necesidad
if simple_product:
    result = fast_client.extract(text)
else:
    result = accurate_client.extract(text)
```

### Optimización de Performance
```python
# En llama_client.py
self.llm = OllamaLLM(
    model="llama3.2:3b",
    temperature=0,
    num_predict=512,      # Limitar tokens (más rápido)
    num_ctx=2048,         # Contexto más corto
    top_k=10,             # Top-k sampling
    top_p=0.9,            # Nucleus sampling
    repeat_penalty=1.1    # Evitar repetición
)
```

---

## 📊 Benchmark de Modelos

### En tu sistema (prueba cada uno):

```bash
# Test de velocidad
time ollama run llama3.2:1b "Extrae: LECHE GLORIA 1L"
time ollama run llama3.2:3b "Extrae: LECHE GLORIA 1L"
time ollama run llama3.1:8b "Extrae: LECHE GLORIA 1L"
```

**Resultados típicos (sin GPU):**
```
llama3.2:1b  → 5-10s  (75% precisión)
llama3.2:3b  → 10-15s (80% precisión)
llama3.1:8b  → 20-30s (85% precisión)
```

**Resultados típicos (con GPU RTX 3060):**
```
llama3.2:1b  → 2-3s   (75% precisión)
llama3.2:3b  → 3-5s   (80% precisión)
llama3.1:8b  → 8-12s  (85% precisión)
```

---

## 🎯 Recomendaciones por Caso

### Desarrollo Local
```bash
ollama pull llama3.2:1b
# Rápido para pruebas
```

### Producción (Servidor con GPU)
```bash
ollama pull llama3.1:8b
# Mejor balance calidad/velocidad
```

### Máxima Precisión (Servidor potente)
```bash
ollama pull llama3.1:70b
# Requiere: 32GB RAM + GPU 24GB
```

### Sin GPU
```bash
ollama pull llama3.2:1b
# Único viable sin GPU
# O mejor: usa Gemini (gratis, en la nube)
```

---

## 📚 Recursos Adicionales

### Documentación
- **Ollama**: https://ollama.com/docs
- **LangChain**: https://python.langchain.com/docs
- **Llama**: https://llama.meta.com

### Comunidad
- **Discord Ollama**: https://discord.gg/ollama
- **GitHub Issues**: https://github.com/ollama/ollama/issues

### Modelos Alternativos
```bash
# Mistral (alternativa a Llama)
ollama pull mistral:7b

# CodeLlama (especializado en código)
ollama pull codellama:7b

# Phi-2 (pequeño pero bueno)
ollama pull phi:2.7b
```

---

## ✅ Checklist Final

- [ ] 1. Ollama instalado (`ollama --version`)
- [ ] 2. Modelo descargado (`ollama list`)
- [ ] 3. Ollama corriendo (`curl http://localhost:11434`)
- [ ] 4. LangChain instalado (`pip install langchain-ollama`)
- [ ] 5. LlamaClient probado (`python test_llama.py`)
- [ ] 6. Integrado en endpoint (`strategy="llama"`)
- [ ] 7. Logs verificados (sin errores)

---

## 🎉 ¡Listo!

Tu sistema ahora tiene:
- ✅ Ollama corriendo localmente
- ✅ Llama 3.2 disponible
- ✅ LlamaClient funcionando
- ✅ Integrado con tu sistema

**Próximo paso:**
Prueba tu endpoint con fotos reales y compara:
- Gemini (nube, gratis, rápido)
- OpenAI (nube, pago, preciso)
- Llama (local, gratis, privado)

Elige el que mejor se adapte a tus necesidades! 🚀
