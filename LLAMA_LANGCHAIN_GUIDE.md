# 🦙 Guía Completa: Llama + LangChain

## 📚 ¿Qué es Llama?

### Concepto
**Llama** es un modelo de lenguaje grande (LLM) de **código abierto** creado por Meta (Facebook).

### Características:
- 🆓 **Gratis**: 100% open-source
- 🏠 **Local**: Corre en TU computadora (no envía datos a internet)
- ⚡ **Rápido**: Si tienes buena GPU
- 🔒 **Privado**: Los datos NUNCA salen de tu servidor

### Versiones Disponibles:
```
Llama 3.2:
├── llama3.2:1b     → 1 billion params (muy rápido, poca precisión)
├── llama3.2:3b     → 3 billion params (balance)
└── llama3.2:11b    → 11 billion params (lento, muy preciso)

Llama 3.1:
├── llama3.1:8b     → 8 billion params (recomendado)
├── llama3.1:70b    → 70 billion params (requiere GPU potente)
└── llama3.1:405b   → 405 billion params (requiere cluster)
```

### ¿Cómo funciona Llama?

```
┌─────────────────────────────────────────────────────┐
│  LLAMA (Modelo de IA)                               │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ENTRADA:  "Texto OCR: Leche Gloria 1L..."         │
│            ↓                                        │
│  PROCESO:  [Neurona Layer 1] → [Layer 2] → ...     │
│            Analiza patterns, extrae entidades       │
│            ↓                                        │
│  SALIDA:   "{ "name": "Leche Gloria", ... }"       │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Ventajas vs Desventajas

| ✅ VENTAJAS | ❌ DESVENTAJAS |
|-------------|----------------|
| Gratis 100% | Requiere GPU/CPU potente |
| Privacidad total | Instalación compleja |
| Sin límites de API | Lento sin GPU |
| Sin internet | Consume RAM (4-16 GB) |
| Personalizable | Menos preciso que GPT-4 |

---

## 🔗 ¿Qué es LangChain?

### Concepto
**LangChain** es un **framework** (conjunto de herramientas) para construir aplicaciones con LLMs.

### Analogía:
```
Si Llama es un "chef" (IA que cocina respuestas)
→ LangChain es la "cocina profesional" (herramientas para trabajar mejor)
```

### ¿Qué hace LangChain?

```python
# ❌ SIN LangChain (complicado)
import requests
response = requests.post("http://localhost:11434/api/generate", {
    "model": "llama3.2",
    "prompt": f"Extrae datos de: {texto}",
    "stream": False
})
data = response.json()['response']
# Necesitas parsear manualmente, manejar errores, etc.

# ✅ CON LangChain (fácil)
from langchain_ollama import OllamaLLM
llm = OllamaLLM(model="llama3.2")
response = llm.invoke("Extrae datos de: " + texto)
# ¡Listo! LangChain maneja todo
```

### Componentes de LangChain

1. **LLMs**: Conexión a modelos (Llama, OpenAI, etc.)
2. **Prompts**: Templates para instrucciones
3. **Chains**: Secuencias de pasos (Prompt → LLM → Parser)
4. **Memory**: Recordar conversaciones anteriores
5. **Agents**: IA que decide qué hacer

---

## 🔄 Flujo Completo en Tu Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USUARIO TOMA FOTOS                                           │
│    📸 Frontal | 📸 Izquierda | 📸 Derecha                       │
└────────────────┬────────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. OCR EXTRAE TEXTO (Pytesseract)                              │
│    Input:  Imágenes (bytes)                                     │
│    Proceso: Tesseract analiza pixeles → texto                   │
│    Output: "LECHE GLORIA\n1000 ml\n7750182001564"              │
└────────────────┬────────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. AI EXTRACTOR (Tu código actual)                             │
│    Elige estrategia: Gemini | OpenAI | Llama | Mock            │
└────────────────┬────────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. LLAMA CLIENT (LangChain)                                    │
│                                                                 │
│    ┌──────────────────────────────────────────┐                │
│    │ A. OLLAMA (Servidor Local)               │                │
│    │    - Corre en http://localhost:11434     │                │
│    │    - Aloja el modelo Llama 3.2           │                │
│    └──────────┬───────────────────────────────┘                │
│               ↓                                                 │
│    ┌──────────────────────────────────────────┐                │
│    │ B. LANGCHAIN (Framework)                 │                │
│    │    - OllamaLLM: Conexión a Ollama        │                │
│    │    - PromptTemplate: Estructura prompt   │                │
│    │    - Chain: Prompt → LLM → Parser        │                │
│    └──────────┬───────────────────────────────┘                │
│               ↓                                                 │
│    ┌──────────────────────────────────────────┐                │
│    │ C. LLAMA MODEL (IA)                      │                │
│    │    Input:  Prompt + OCR text             │                │
│    │    Proceso: Neural network processing    │                │
│    │    Output: JSON string                   │                │
│    └──────────┬───────────────────────────────┘                │
│               ↓                                                 │
│    ┌──────────────────────────────────────────┐                │
│    │ D. JSON PARSER (Tu código)               │                │
│    │    - Limpia markdown (```)               │                │
│    │    - Extrae JSON con regex               │                │
│    │    - Parsea con json.loads()             │                │
│    └──────────┬───────────────────────────────┘                │
└───────────────┼─────────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. RESULTADO FINAL                                              │
│    {                                                            │
│      "name": "Leche Gloria Entera",                            │
│      "brand": "Gloria",                                         │
│      "size": "1000ml",                                          │
│      ...                                                        │
│    }                                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Desglose Técnico

### 1. OLLAMA (Servidor)

**¿Qué hace?**
- Aloja modelos LLM localmente
- API REST para comunicación
- Maneja memoria GPU/CPU

**Instalación:**
```bash
# Linux/Mac
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# Descargar de: https://ollama.com/download

# Verificar instalación
ollama --version
```

**Descargar modelo:**
```bash
# Llama 3.2 (1B - rápido)
ollama pull llama3.2:1b

# Llama 3.2 (3B - recomendado)
ollama pull llama3.2:3b

# Llama 3.1 (8B - más preciso)
ollama pull llama3.1:8b
```

**Servidor corre en:**
```
http://localhost:11434
```

**Ejemplo de request directo:**
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "¿Qué es Python?"
}'
```

---

### 2. LANGCHAIN (Framework)

**Componentes que usas:**

#### A. OllamaLLM
```python
from langchain_ollama import OllamaLLM

llm = OllamaLLM(
    model="llama3.2",      # Modelo a usar
    temperature=0,         # 0 = determinista, 1 = creativo
    base_url="http://localhost:11434"  # Servidor Ollama
)

# Entrada: String (prompt)
# Salida: String (respuesta del modelo)
response = llm.invoke("¿Cuál es la capital de Perú?")
# → "La capital de Perú es Lima."
```

#### B. PromptTemplate
```python
from langchain_core.prompts import PromptTemplate

template = PromptTemplate(
    input_variables=["producto", "precio"],
    template="""
    Producto: {producto}
    Precio: {precio}
    
    ¿Es caro o barato?
    """
)

# Entrada: Dict con variables
# Salida: Prompt formateado
prompt = template.format(producto="iPhone", precio="$1000")
# → "Producto: iPhone\nPrecio: $1000\n¿Es caro o barato?"
```

#### C. Chain (Cadena)
```python
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

template = PromptTemplate(...)
llm = OllamaLLM(...)

# Crear cadena (prompt → llm)
chain = template | llm

# Entrada: Dict
# Proceso: Template formatea → LLM procesa
# Salida: String
response = chain.invoke({"producto": "iPhone", "precio": "$1000"})
```

---

### 3. TU CÓDIGO ACTUAL (LlamaClient)

```python
class LlamaClient:
    def __init__(self):
        # PASO 1: Conectar a Ollama
        self.llm = OllamaLLM(model="llama3.2", temperature=0)
        
        # PASO 2: Crear template del prompt
        self.prompt = PromptTemplate(
            input_variables=["ocr_text"],
            template="Extrae datos de: {ocr_text}"
        )
    
    def extract(self, ocr_text: str) -> dict:
        # PASO 3: Crear chain (template + llm)
        chain = self.prompt | self.llm
        
        # PASO 4: Ejecutar
        # Input: {"ocr_text": "LECHE GLORIA 1L..."}
        # Output: "```json\n{...}\n```"
        response = chain.invoke({"ocr_text": ocr_text})
        
        # PASO 5: Limpiar y parsear JSON
        return self._extract_json_from_response(response)
```

---

## 📊 Comparación: Llama vs Gemini vs OpenAI

| Aspecto | Llama 3.2 | Gemini | OpenAI |
|---------|-----------|---------|---------|
| **Ubicación** | Tu servidor | Nube Google | Nube OpenAI |
| **Latencia** | 2-10s | 2-3s | 3-5s |
| **Privacidad** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **Costo** | $0 (electricidad) | $0 (gratis) | $0.001/req |
| **Precisión** | ⭐⭐⭐ 75% | ⭐⭐⭐⭐ 85% | ⭐⭐⭐⭐⭐ 92% |
| **Setup** | ⚠️ Complejo | ✅ Fácil | ✅ Fácil |
| **RAM necesaria** | 4-16 GB | 0 | 0 |
| **GPU necesaria** | Recomendada | No | No |

---

## 🎯 ¿Cuándo usar Llama?

### ✅ USA LLAMA cuando:
- Manejas datos sensibles (privacidad crítica)
- Tienes buena GPU (RTX 3060+ o similar)
- Quieres evitar costos de API
- Tienes volumen MUY alto (>100k requests/día)
- No tienes internet confiable

### ❌ NO USES LLAMA cuando:
- No tienes GPU (será MUY lento)
- Necesitas máxima precisión
- Quieres desarrollo rápido (usa Gemini)
- Tienes presupuesto para APIs

---

## 💻 Requisitos de Hardware

### Mínimo (Llama 3.2:1b)
```
CPU: 4 cores
RAM: 4 GB
GPU: Ninguna (lento)
Velocidad: ~15s por request
```

### Recomendado (Llama 3.2:3b)
```
CPU: 6 cores
RAM: 8 GB
GPU: NVIDIA GTX 1660 (6 GB VRAM)
Velocidad: ~3s por request
```

### Óptimo (Llama 3.1:8b)
```
CPU: 8 cores
RAM: 16 GB
GPU: NVIDIA RTX 3060 (12 GB VRAM)
Velocidad: ~2s por request
```

---

## 🔧 Próximos pasos

Te voy a crear una versión mejorada de tu `LlamaClient` con:
- ✅ Mejor manejo de errores
- ✅ Validación de Ollama
- ✅ Logs detallados
- ✅ Múltiples modelos
- ✅ Retry automático
- ✅ Timeout configurable

¿Quieres que continúe con el código mejorado? 🚀
