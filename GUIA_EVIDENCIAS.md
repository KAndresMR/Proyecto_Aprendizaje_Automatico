# 📸 GUÍA PARA MOSTRAR EVIDENCIAS

Esta guía te indica **paso a paso** cómo demostrar que todos los componentes están funcionando.

---

## 🎯 OBJETIVO

Demostrar que:
1. ✅ ChromaDB está guardando embeddings
2. ✅ LangChain está integrado y funcionando
3. ✅ PostgreSQL guarda datos correctamente
4. ✅ Todo el sistema funciona end-to-end

---

## 📋 CHECKLIST DE EVIDENCIAS

### ✅ Evidencia 1: ChromaDB Funcionando

**Qué ejecutar:**
```bash
cd backend  # o donde esté tu proyecto
python ../chroma_langchain_integration.py
```

**Qué va a pasar:**
- Se creará carpeta `chroma_evidence_db/` con los vectores
- Se mostrarán logs detallados en colores
- Se generará archivo `integration_evidence_report_XXXXXX.json`

**Qué mostrar:**
1. **Terminal con logs** - Captura de pantalla mostrando:
   - `✅ ChromaDB importado correctamente`
   - `✅ 5 productos agregados en X.XXs`
   - `✅ Búsqueda completada en XXms`
   
2. **Carpeta chroma_evidence_db/** - Mostrar con:
   ```bash
   ls -la chroma_evidence_db/
   ```
   Debe mostrar archivos `.parquet` con los embeddings

3. **Archivo JSON de reporte** - Abrir y mostrar:
   ```bash
   cat integration_evidence_report_*.json
   ```
   
4. **Explicar**: "Aquí está ChromaDB guardando los embeddings de los productos. Cada producto tiene su vector de 384 dimensiones."

---

### ✅ Evidencia 2: LangChain Funcionando

**Qué ejecutar:**
```bash
python ../test_evidencias.py
```

**Qué va a pasar:**
- Se ejecutarán 6 tests
- Test 2 específico muestra LangChain
- Se generará `evidencias_test_XXXXXX.json`

**Qué mostrar:**
1. **Terminal - Sección de LangChain:**
   ```
   ═══════════════════════════════════════
   🔍 TEST 2: LANGCHAIN + LLAMA
   ═══════════════════════════════════════
   ✅ PromptTemplate creado
   ✅ LLM Chain: ✅ Funcionando
   ```

2. **Explicar**: "LangChain está configurado con un PromptTemplate que estructura cómo le pedimos al LLM que extraiga información."

3. **Mostrar código** en `backend/app/services/ai/llama_client.py` (si existe) o en el script de evidencias

---

### ✅ Evidencia 3: PostgreSQL con Datos

**Qué ejecutar:**
```bash
python ../db_evidencias.py
```

**Qué va a pasar:**
- Se conecta a PostgreSQL
- Muestra tablas en formato tabla
- Muestra productos, lotes, logs OCR
- Exporta un JSON de ejemplo

**Qué mostrar:**
1. **Terminal con tablas:**
   ```
   ┌────┬──────────────────┬──────────┬────────────┬────────┐
   │ #  │ Tabla            │ Columnas │ Registros  │ Estado │
   ├────┼──────────────────┼──────────┼────────────┼────────┤
   │  1 │ products         │ 12       │ 15         │ ✅     │
   │  2 │ product_batches  │ 9        │ 22         │ ✅     │
   │  3 │ ocr_logs         │ 6        │ 45         │ ✅     │
   └────┴──────────────────┴──────────┴────────────┴────────┘
   ```

2. **Abrir PgAdmin o DBeaver** y mostrar visualmente:
   - Tabla `products` con registros
   - Tabla `product_batches` con lotes
   
3. **Mostrar archivo JSON exportado:**
   ```bash
   cat sample_product_*.json
   ```

4. **Explicar**: "Aquí puede ver que la base de datos está guardando todos los productos que procesamos. Cada producto tiene su información completa."

---

### ✅ Evidencia 4: Sistema Completo (End-to-End)

**Qué hacer:**
1. Abrir la aplicación web: `http://localhost:3000` (o tu URL de Render)
2. Capturar 3 fotos de un producto (usar un producto real)
3. Mostrar el proceso en vivo

**Qué mostrar:**

**Paso 1 - Captura:**
- "Aquí tomo las 3 fotos del producto"
- Mostrar la interfaz guiando la captura

**Paso 2 - Procesamiento:**
- "Ahora se está procesando con OCR + IA"
- Mostrar overlay de loading con progreso

**Paso 3 - Logs en terminal del backend:**
```bash
# En otra ventana, mostrar logs del backend:
uvicorn main:app --reload

# Logs que aparecerán:
📸 Iniciando procesamiento optimizado...
💾 Guardando imágenes...
⏱️ Guardado: 0.25s
🔍 Ejecutando OCR optimizado...
⏱️ OCR: 3.42s
🤖 Extrayendo información con Gemini...
⏱️ IA Extracción: 4.15s
✅ Procesamiento completado en 8.50s
```

**Paso 4 - Formulario:**
- Mostrar formulario con datos pre-llenados
- "Mire, la IA extrajo automáticamente: nombre, marca, tamaño, etc."

**Paso 5 - Confirmación:**
- Guardar el producto
- Mostrar confirmación por voz (si está configurado ElevenLabs)

**Paso 6 - Verificar en BD:**
```bash
# En otra terminal
python db_evidencias.py
```
- "Y ahora puede ver que el producto se guardó en la base de datos"

---

### ✅ Evidencia 5: Deduplicación Funcionando

**Qué hacer:**
1. Registrar un producto (ej: Coca-Cola)
2. Intentar registrar el mismo producto otra vez
3. Mostrar que detecta el duplicado

**Qué mostrar:**

**En logs del backend:**
```
🔍 Buscando duplicados...
🔄 Producto duplicado detectado: Coca Cola Sin Azúcar
   Similitud: 98.5%
✓ Stock incrementado de 1 a 2
```

**Explicar**: "El sistema usa embeddings vectoriales para detectar productos duplicados, incluso si el texto no es exactamente igual. Aquí detectó que era el mismo producto y solo incrementó el stock."

---

## 📸 CAPTURAS DE PANTALLA RECOMENDADAS

Toma capturas de pantalla de:

1. **Terminal con logs de ChromaDB** (chroma_langchain_integration.py)
2. **Terminal con tabla de PostgreSQL** (db_evidencias.py)  
3. **Carpeta chroma_evidence_db/ con archivos** (ls -la)
4. **PgAdmin mostrando tabla products** con datos
5. **Interfaz web - Flujo completo** (4-5 screenshots):
   - Captura de fotos
   - Procesamiento
   - Formulario con datos
   - Confirmación
6. **Logs del backend en tiempo real** durante procesamiento

---

## 🎬 DEMO EN VIVO - Guion Sugerido

### Duración: 5-7 minutos

**Minuto 0-1: Introducción**
- "Voy a mostrar el sistema funcionando end-to-end"
- "Tenemos 3 componentes principales: ChromaDB para embeddings, LangChain para extracción, y PostgreSQL para datos"

**Minuto 1-3: Evidencias Técnicas**
- Ejecutar `chroma_langchain_integration.py`
- Mostrar logs
- Abrir carpeta de ChromaDB
- "Aquí puede ver los embeddings guardados"

**Minuto 3-4: Base de Datos**
- Ejecutar `db_evidencias.py`
- Mostrar tablas
- Abrir PgAdmin
- "Aquí están los productos que hemos registrado"

**Minuto 4-7: Sistema en Vivo**
- Abrir aplicación web
- Tomar 3 fotos de un producto real
- Mostrar procesamiento
- Mostrar logs en terminal del backend
- Guardar producto
- Verificar que se guardó en BD

**Cierre:**
- "Como puede ver, todos los componentes están integrados y funcionando"
- Mostrar README con arquitectura

---

## 📁 ARCHIVOS DE EVIDENCIA A ENTREGAR

Crear una carpeta `EVIDENCIAS/` con:

```
EVIDENCIAS/
├── capturas/
│   ├── 01_chromadb_logs.png
│   ├── 02_chromadb_folder.png
│   ├── 03_postgresql_table.png
│   ├── 04_pgadmin_products.png
│   ├── 05_web_captura.png
│   ├── 06_web_procesamiento.png
│   ├── 07_web_formulario.png
│   └── 08_backend_logs.png
│
├── archivos_json/
│   ├── integration_evidence_report.json
│   ├── evidencias_test.json
│   └── sample_product.json
│
├── logs/
│   ├── chromadb_output.txt
│   ├── db_evidencias_output.txt
│   └── backend_logs.txt
│
└── video/
    └── demo_completo.mp4  (CapCut - 3 min)
```

---

## 💡 TIPS PARA LA PRESENTACIÓN

1. **Preparar todo antes:**
   - Tener ChromaDB ya con datos
   - Tener algunos productos en PostgreSQL
   - Backend corriendo en background
   - Terminal con logs visible

2. **Tener ventanas abiertas:**
   - Terminal 1: Para ejecutar scripts de evidencia
   - Terminal 2: Logs del backend (uvicorn)
   - Navegador: Aplicación web
   - PgAdmin/DBeaver: Ver base de datos
   - VS Code: Para mostrar código si pregunta

3. **Ensayar el flujo:**
   - Practica la demo 2-3 veces
   - Ten a mano un producto físico para capturar
   - Conoce dónde está cada evidencia

4. **Tener respuestas preparadas:**
   - "¿Por qué ChromaDB?" → "Para búsqueda semántica de duplicados"
   - "¿Por qué LangChain?" → "Para estructurar prompts y trabajar con LLMs"
   - "¿Dónde está el código?" → Mostrar `services/ai/` y `services/vector_service.py`

---

## 🚨 SI ALGO FALLA

### ChromaDB no funciona:
```bash
pip install --upgrade chromadb
python chroma_langchain_integration.py
```

### PostgreSQL no conecta:
- Verificar que esté corriendo: `sudo systemctl status postgresql`
- Verificar credenciales en `.env`

### Backend da error:
- Ver logs: `tail -f backend/logs/app.log`
- Reiniciar: `Ctrl+C` y volver a ejecutar uvicorn

---

## ✅ CHECKLIST FINAL ANTES DE PRESENTAR

- [ ] ChromaDB funciona (ejecutar script)
- [ ] LangChain funciona (ejecutar script)
- [ ] PostgreSQL tiene datos (verificar con script)
- [ ] Backend corriendo sin errores
- [ ] Frontend accesible
- [ ] Capturas de pantalla tomadas
- [ ] Video grabado y editado (CapCut)
- [ ] README completo
- [ ] Notebooks con gráficas
- [ ] Carpeta EVIDENCIAS/ organizada

---

**¡Listo! Con esto tienes evidencias SÓLIDAS de que todo funciona. Suerte en la presentación! 🚀**
