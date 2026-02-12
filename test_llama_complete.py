"""
Script de prueba para LlamaClient
==================================

Ejecuta pruebas básicas para verificar que Llama está funcionando correctamente.

Uso:
    python test_llama_complete.py
"""

import sys
import time
from typing import Dict



# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text:^60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_error(text: str):
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")

def print_info(text: str):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")


def test_imports():
    """Prueba 1: Verificar importaciones"""
    print_header("PRUEBA 1: Verificando Dependencias")
    
    errors = []
    
    # LangChain
    try:
        from langchain_ollama import OllamaLLM
        from langchain_core.prompts import PromptTemplate
        print_success("LangChain instalado correctamente")
    except ImportError as e:
        print_error(f"LangChain no instalado: {e}")
        errors.append("langchain")
    
    # Requests
    try:
        import requests
        print_success("Requests instalado correctamente")
    except ImportError:
        print_error("Requests no instalado")
        errors.append("requests")
    
    if errors:
        print_warning(f"Instala dependencias faltantes: pip install {' '.join(errors)}")
        return False
    
    return True


def test_ollama_server():
    """Prueba 2: Verificar servidor Ollama"""
    print_header("PRUEBA 2: Verificando Servidor Ollama")
    
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        
        if response.status_code == 200:
            print_success("Ollama está corriendo")
            
            models = response.json().get("models", [])
            if models:
                print_info(f"Modelos disponibles ({len(models)}):")
                for m in models:
                    print(f"   • {m['name']}")
            else:
                print_warning("No hay modelos descargados")
                print_info("Descarga uno con: ollama pull llama3.2:latest")
                return False
            
            return True
        else:
            print_error(f"Ollama respondió con código: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException:
        print_error("Ollama no está corriendo")
        print_info("Inicia Ollama con: ollama serve")
        return False


def test_llama_client():
    """Prueba 3: Verificar LlamaClient"""
    print_header("PRUEBA 3: Verificando LlamaClient")
    
    try:
        # Intentar importar desde tu proyecto
        try:
            from .backend.app.services.ai.llama_client import LlamaClient
            print_info(f"LlamaClient importado desde: {LlamaClient.__module__}")
            print_info(f"Archivo: {LlamaClient.__init__.__code__.co_filename}")
            print_success("LlamaClient importado desde proyecto")
        except ImportError:
            # Si falla, usar versión local
            import sys
            import os
            sys.path.insert(0, os.path.dirname(__file__))
            from backend.app.services.ai.llama_client import LlamaClient
            print_success("LlamaClient importado (versión local)")
        
        # Crear cliente
        client = LlamaClient(model="llama3.2:latest")
        
        if client.is_available():
            print_success("LlamaClient inicializado correctamente")
            
            # Mostrar info del modelo
            info = client.get_model_info()
            print_info(f"Modelo activo: {info.get('model')}")
            
            return client
        else:
            print_error("LlamaClient no disponible")
            return None
            
    except Exception as e:
        print_error(f"Error creando LlamaClient: {e}")
        return None


def test_extraction(client):
    """Prueba 4: Prueba de extracción"""
    print_header("PRUEBA 4: Prueba de Extracción")
    
    test_cases = [
        {
            "name": "Producto Simple",
            "ocr_text": """
LECHE GLORIA
ENTERA
Contenido neto: 1000 ml
Precio: S/ 5.50
            """,
            "expected_fields": ["name", "brand", "size", "price"]
        },
        {
            "name": "Producto con Lote y Vencimiento",
            "ocr_text": """
COCA COLA
Original
500 ml
Lote: L20250212
Vence: 15/06/2025
Precio: S/ 3.00
            """,
            "expected_fields": ["name", "brand", "size", "batch", "expiry_date", "price"]
        },
        {
            "name": "OCR con Errores",
            "ocr_text": """
L3CHE GL0RIA
3NT3RA
1OOO m1
S/ 5.5O
            """,
            "expected_fields": ["name", "brand", "size"]
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{Colors.BOLD}Test {i}: {test_case['name']}{Colors.RESET}")
        print(f"OCR Input:\n{test_case['ocr_text'][:100]}...")
        
        try:
            start_time = time.time()
            result = client.extract(test_case['ocr_text'])
            elapsed = time.time() - start_time
            
            # Verificar campos esperados
            found_fields = [
                field for field in test_case['expected_fields']
                if result.get(field)
            ]
            
            success_rate = len(found_fields) / len(test_case['expected_fields'])
            
            print(f"⏱️  Tiempo: {elapsed:.2f}s")
            print(f"📊 Campos encontrados: {len(found_fields)}/{len(test_case['expected_fields'])}")
            
            if success_rate >= 0.6:
                print_success(f"Test pasado ({success_rate*100:.0f}%)")
                print(f"   Nombre: {result.get('name')}")
                print(f"   Marca: {result.get('brand')}")
                print(f"   Tamaño: {result.get('size')}")
                if result.get('price'):
                    print(f"   Precio: {result.get('price')}")
            else:
                print_warning(f"Test parcialmente exitoso ({success_rate*100:.0f}%)")
            
            results.append({
                "test": test_case['name'],
                "success": success_rate >= 0.6,
                "rate": success_rate,
                "time": elapsed
            })
            
        except Exception as e:
            print_error(f"Test falló: {e}")
            results.append({
                "test": test_case['name'],
                "success": False,
                "rate": 0,
                "time": 0
            })
    
    return results


def print_summary(results):
    """Muestra resumen de resultados"""
    print_header("RESUMEN DE PRUEBAS")
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['success'])
    avg_time = sum(r['time'] for r in results) / len(results) if results else 0
    avg_rate = sum(r['rate'] for r in results) / len(results) if results else 0
    
    print(f"Tests ejecutados: {total_tests}")
    print(f"Tests exitosos: {passed_tests}/{total_tests}")
    print(f"Tiempo promedio: {avg_time:.2f}s")
    print(f"Precisión promedio: {avg_rate*100:.1f}%")
    
    if passed_tests == total_tests:
        print_success("\n¡Todos los tests pasaron! ✨")
    elif passed_tests >= total_tests * 0.7:
        print_warning(f"\n{passed_tests}/{total_tests} tests pasaron. Aceptable.")
    else:
        print_error(f"\nSolo {passed_tests}/{total_tests} tests pasaron. Revisa configuración.")


def main():
    """Función principal"""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("┌─────────────────────────────────────────────────────────┐")
    print("│                                                         │")
    print("│         🦙 LLAMA CLIENT - TEST SUITE 🧪                │")
    print("│                                                         │")
    print("└─────────────────────────────────────────────────────────┘")
    print(Colors.RESET)
    
    # Prueba 1: Imports
    if not test_imports():
        print_error("\n⛔ Abortando: Faltan dependencias\n")
        sys.exit(1)
    
    # Prueba 2: Ollama
    if not test_ollama_server():
        print_error("\n⛔ Abortando: Ollama no disponible\n")
        sys.exit(1)
    
    # Prueba 3: LlamaClient
    client = test_llama_client()
    if not client:
        print_error("\n⛔ Abortando: LlamaClient no disponible\n")
        sys.exit(1)
    
    # Prueba 4: Extracción
    results = test_extraction(client)
    
    # Resumen
    print_summary(results)
    
    print(f"\n{Colors.GREEN}✨ Suite de pruebas completada ✨{Colors.RESET}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️  Pruebas canceladas por el usuario{Colors.RESET}\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error inesperado: {e}{Colors.RESET}\n")
        sys.exit(1)
