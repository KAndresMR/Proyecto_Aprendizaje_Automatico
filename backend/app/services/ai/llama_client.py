import json
import logging
import re

from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)

class LlamaClient:
    def __init__(self):
        try:
            self.llm = OllamaLLM(model="llama3.2", temperature=0)
            
            self.prompt = PromptTemplate(
                input_variables=["ocr_text"],
                template="""Extrae información de este producto. Responde SOLO con JSON válido.

Texto OCR:
{ocr_text}

JSON esperado:
{{
  "name": "nombre del producto",
  "brand": "marca",
  "size": "tamaño con unidad",
  "barcode": "código de barras",
  "price": número o null
}}

JSON:"""
            )
            logger.info("✅ Llama 3.2 inicializado")
        except Exception as e:
            logger.error(f"❌ Error inicializando Llama: {e}")
            self.llm = None
    
    def extract(self, ocr_text: str) -> dict:
        """Extraer con Llama"""
        if not self.llm:
            raise Exception("Llama no disponible")
        
        try:
            chain = self.prompt | self.llm
            response = chain.invoke({"ocr_text": ocr_text})
            
            # ✅ ARREGLADO: Método de instancia con self
            return self._extract_json_from_response(response)
            
        except Exception as e:
            logger.error(f"❌ Error Llama: {e}")
            raise
    
    def _extract_json_from_response(self, response: str) -> dict:
        """Extraer JSON de respuesta de Llama"""
        response = response.strip()
        
        # Limpiar markdown
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
            response = response.strip()
        
        # Buscar JSON en la respuesta
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            response = json_match.group()
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON: {response[:200]}")
            raise

# Instancia global
llama_client = LlamaClient()