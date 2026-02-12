import json
import logging
import re
import time
from typing import Dict, Optional, List
from datetime import datetime

try:
    from langchain_ollama import OllamaLLM
    from langchain_core.prompts import PromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logging.warning("⚠️ langchain-ollama no instalado. Usa: pip install langchain-ollama")

import requests

logger = logging.getLogger(__name__)


class LlamaClient:
    """
    Cliente para extraer información de productos usando Llama local.
    
    ENTRADA (extract method):
        ocr_text: str - Texto extraído por OCR
        
    SALIDA (extract method):
        dict - JSON estructurado con datos del producto
        
    EJEMPLO:
        client = LlamaClient()
        result = client.extract("LECHE GLORIA 1L...")
        # → {"name": "Leche Gloria", "brand": "Gloria", ...}
    """
    
    # Modelos disponibles (ordenados por calidad)
    AVAILABLE_MODELS = [
        "llama3.2:3b",    # Recomendado (balance)
        "llama3.2:1b",    # Rápido (menos preciso)
        "llama3.1:8b",    # Más preciso (más lento)
        "llama3.2",       # Alias de 3b
    ]
    
    def __init__(
        self,
        model: str = "llama3.2:latest",
        base_url: str = "http://localhost:11434",
        timeout: int = 60,
        max_retries: int = 2
    ):
        """
        Inicializa el cliente Llama.
        
        Args:
            model: Modelo a usar (ej: "llama3.2:latest")
            base_url: URL del servidor Ollama
            timeout: Tiempo máximo de espera (segundos)
            max_retries: Reintentos en caso de error
        """
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.llm = None
        self.prompt = None
        
        # Verificar que LangChain está disponible
        if not LANGCHAIN_AVAILABLE:
            logger.error("❌ LangChain no está instalado")
            logger.info("💡 Instala con: pip install langchain-ollama")
            return
        
        # Verificar que Ollama está corriendo
        if not self._check_ollama_server():
            logger.error(f"❌ Ollama no está corriendo en {base_url}")
            logger.info("💡 Inicia Ollama con: ollama serve")
            return
        
        # Verificar que el modelo está descargado
        if not self._check_model_exists():
            logger.error(f"❌ Modelo '{model}' no encontrado")
            logger.info(f"💡 Descarga con: ollama pull {model}")
            self._suggest_alternative_models()
            return
        
        # Inicializar LLM
        try:
            self.llm = OllamaLLM(
                model=model,
                base_url=base_url,
                temperature=0,  # Determinista
                timeout=timeout,
                num_predict=1024,  # Tokens máximos de respuesta
            )
            
            # Crear prompt template
            self.prompt = self._create_prompt_template()
            
            logger.info(f"✅ Llama inicializado: {model}")
            logger.info(f"🌐 Servidor: {base_url}")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando Llama: {e}")
            self.llm = None
    
    def _check_ollama_server(self) -> bool:
        """Verifica que el servidor Ollama está corriendo"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def _check_model_exists(self) -> bool:
        """Verifica que el modelo está descargado"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                return False
            
            models = response.json().get("models", [])
            model_names = [m["name"] for m in models]
            
            # Verificar modelo exacto o base
            model_base = self.model.split(":")[0]  # "llama3.2:latest" → "llama3.2"
            
            return any(
                self.model in name or model_base in name
                for name in model_names
            )
            
        except Exception:
            return False
    
    def _suggest_alternative_models(self):
        """Sugiere modelos alternativos disponibles"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                if models:
                    logger.info("📦 Modelos disponibles:")
                    for m in models:
                        logger.info(f"   - {m['name']}")
        except Exception:
            pass
    
    def _create_prompt_template(self) -> PromptTemplate:
        """Crea el template del prompt para extracción"""
        return PromptTemplate(
            input_variables=["ocr_text"],
            template="""Eres un experto en análisis de productos de consumo.

Extrae información estructurada del siguiente texto OCR.
El texto puede contener errores de OCR y estar desordenado.

TEXTO OCR:
{ocr_text}

INSTRUCCIONES:
1. Corrige errores de OCR
2. Extrae toda la información posible
3. Si no encuentras un valor, usa null
4. Responde SOLO con JSON válido (sin markdown, sin explicaciones)

ESTRUCTURA JSON REQUERIDA:
{{
  "name": null,
  "brand": null,
  "presentation": null,
  "size": null,
  "barcode": null,
  "batch": null,
  "expiry_date": null,
  "price": null,
  "category": null,
  "nutritional_info": {{
    "calories": null,
    "protein": null,
    "carbs": null,
    "fat": null,
    "sodium": null
  }}
}}

JSON:"""
        )
    
    def extract(self, ocr_text: str) -> Dict:
        """
        Extrae información del producto desde texto OCR.
        
        FLUJO:
        1. Valida que Llama está disponible
        2. Crea la cadena (Prompt + LLM)
        3. Ejecuta la inferencia
        4. Parsea y valida JSON
        5. Retorna resultado
        
        Args:
            ocr_text: Texto extraído por OCR
            
        Returns:
            Dict con información del producto
            
        Raises:
            Exception: Si Llama no está disponible o falla la extracción
        """
        # Validar disponibilidad
        if not self.llm:
            raise Exception(
                "Llama no está disponible. "
                "Verifica que Ollama esté corriendo y el modelo descargado."
            )
        
        # Validar entrada
        if not ocr_text or not ocr_text.strip():
            raise ValueError("OCR text está vacío")
        
        logger.info(f"🦙 Extrayendo con Llama | Texto length: {len(ocr_text)}")
        
        # Intentar extracción con retries
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                start_time = time.time()
                
                # Crear cadena (Prompt → LLM)
                chain = self.prompt | self.llm
                # Ejecutar inferencia
                logger.info(f"🔄 Intento {attempt}/{self.max_retries}")
                response = chain.invoke({"ocr_text": ocr_text})
                if not isinstance(response, str):
                    response = str(response)
                
                elapsed = time.time() - start_time
                logger.info(f"⏱️  Llama respondió en {elapsed:.2f}s")
                
                # Parsear JSON de la respuesta
                result = self._extract_json_from_response(response)
                
                # Validar estructura
                self._validate_result(result)
                
                logger.info(f"✅ Extracción exitosa con Llama")
                return result
                
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️  Intento {attempt} falló: {e}")
                
                if attempt < self.max_retries:
                    wait_time = attempt * 2  # Backoff exponencial
                    logger.info(f"⏳ Reintentando en {wait_time}s...")
                    time.sleep(wait_time)
        
        # Si llegamos aquí, todos los intentos fallaron
        logger.error(f"❌ Llama falló después de {self.max_retries} intentos")
        raise last_error
    
    def _extract_json_from_response(self, response: str) -> Dict:
        """
        Extrae y parsea JSON de la respuesta de Llama.
        
        PROBLEMA: Llama a veces responde con:
        ```json
        {"name": "..."}
        ```
        
        SOLUCIÓN: Limpiar markdown y extraer JSON puro
        
        Args:
            response: Respuesta cruda de Llama
            
        Returns:
            Dict parseado
            
        Raises:
            json.JSONDecodeError: Si no se puede parsear
        """
        original_response = response
        response = response.strip()
        
        # PASO 1: Limpiar markdown
        # Remover ```json ... ```
        if response.startswith("```"):
            lines = response.split("\n")
            # Remover primera línea (```json)
            if lines[0].strip().startswith("```"):
                lines = lines[1:]
            # Remover última línea (```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)
        
        # PASO 2: Buscar JSON en la respuesta
        # Patrón: { ... } (incluso con saltos de línea)
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        
        if json_match:
            response = json_match.group()
        
        # PASO 3: Parsear JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON de Llama:")
            logger.error(f"Respuesta original: {original_response[:500]}")
            logger.error(f"Después de limpieza: {response[:500]}")
            raise ValueError(f"Llama no devolvió JSON válido: {str(e)}")
    
    def _validate_result(self, result: Dict):
        """
        Valida que el resultado tenga la estructura correcta.
        
        Args:
            result: Dict a validar
            
        Raises:
            ValueError: Si falta alguna clave requerida
        """
        required_keys = [
            "name", "brand", "presentation", "size", "barcode",
            "batch", "expiry_date", "price", "category", "nutritional_info"
        ]
        
        missing_keys = [key for key in required_keys if key not in result]
        
        if missing_keys:
            raise ValueError(
                f"Estructura incompleta de Llama. "
                f"Claves faltantes: {missing_keys}"
            )
        
        # Validar nutritional_info
        if not isinstance(result["nutritional_info"], dict):
            raise ValueError("nutritional_info debe ser un diccionario")
    
    def get_model_info(self) -> Dict:
        """
        Obtiene información del modelo activo.
        
        Returns:
            Dict con metadata del modelo
        """
        if not self.llm:
            return {"error": "Llama no disponible"}
        
        try:
            response = requests.post(
                f"{self.base_url}/api/show",
                json={"name": self.model},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "model": self.model,
                    "size": data.get("size", "unknown"),
                    "modified": data.get("modified_at", "unknown"),
                    "available": True
                }
        except Exception as e:
            logger.error(f"Error obteniendo info del modelo: {e}")
        
        return {
            "model": self.model,
            "available": self.llm is not None
        }
    
    def is_available(self) -> bool:
        """Verifica si Llama está listo para usar"""
        return self.llm is not None


# ========================================
# INSTANCIA GLOBAL
# ========================================

try:
    llama_client = LlamaClient(
        model="llama3.2:latest",  # Cambia según tu modelo
        timeout=60
    )
    
    if llama_client.is_available():
        logger.info("✅ LlamaClient global inicializado")
        info = llama_client.get_model_info()
        logger.info(f"📦 Modelo: {info.get('model')}")
    else:
        logger.warning("⚠️ LlamaClient no disponible")
        llama_client = None
        
except Exception as e:
    logger.error(f"❌ Error creando LlamaClient global: {e}")
    llama_client = None


# ========================================
# UTILIDADES
# ========================================

def test_llama_connection():
    """
    Prueba la conexión con Ollama.
    Útil para debugging.
    """
    print("\n🔍 Probando conexión con Llama...\n")
    
    # 1. Verificar Ollama
    print("1️⃣ Verificando servidor Ollama...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("   ✅ Ollama está corriendo")
            
            models = response.json().get("models", [])
            if models:
                print(f"   📦 Modelos disponibles ({len(models)}):")
                for m in models:
                    print(f"      - {m['name']}")
            else:
                print("   ⚠️  No hay modelos descargados")
                print("   💡 Descarga uno con: ollama pull llama3.2:latest")
        else:
            print("   ❌ Ollama respondió con error")
    except requests.exceptions.RequestException:
        print("   ❌ Ollama no está corriendo")
        print("   💡 Inicia con: ollama serve")
        return
    
    # 2. Verificar LangChain
    print("\n2️⃣ Verificando LangChain...")
    if LANGCHAIN_AVAILABLE:
        print("   ✅ langchain-ollama instalado")
    else:
        print("   ❌ langchain-ollama no instalado")
        print("   💡 Instala con: pip install langchain-ollama")
        return
    
    # 3. Probar LlamaClient
    print("\n3️⃣ Probando LlamaClient...")
    try:
        client = LlamaClient()
        if client.is_available():
            print("   ✅ LlamaClient inicializado")
            
            # Prueba simple
            print("\n4️⃣ Probando extracción...")
            test_text = "LECHE GLORIA\nENTERA\n1000 ml\nS/ 5.50"
            
            result = client.extract(test_text)
            
            print("   ✅ Extracción exitosa:")
            print(f"      - Nombre: {result.get('name')}")
            print(f"      - Marca: {result.get('brand')}")
            print(f"      - Tamaño: {result.get('size')}")
            print(f"      - Precio: {result.get('price')}")
        else:
            print("   ❌ LlamaClient no disponible")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n✨ Prueba completada\n")


if __name__ == "__main__":
    # Ejecutar prueba si se corre directamente
    test_llama_connection()
