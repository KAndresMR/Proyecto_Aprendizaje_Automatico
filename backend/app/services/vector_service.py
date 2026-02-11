import chromadb
import logging

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path="./chroma_db"
        )
        
        try:
            self.collection = self.client.get_collection("products")
        except:
            self.collection = self.client.create_collection(
                "products",
                metadata={"hnsw:space": "cosine"}
            )
        
        logger.info("✅ Chroma Vector DB inicializado")
    
    def add_product(self, product_id: int, text: str):
        """Guardar embedding de producto"""
        try:
            self.collection.add(
                documents=[text],
                ids=[str(product_id)]
            )
            logger.info(f"📊 Embedding guardado para producto {product_id}")
        except Exception as e:
            logger.error(f"❌ Error guardando embedding: {e}")
    
    def search_similar(self, query_text: str, top_k: int = 5):
        """Buscar productos similares"""
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=top_k
            )
            return results
        except Exception as e:
            logger.error(f"❌ Error buscando similares: {e}")
            return None

# Instancia global
vector_service = VectorService()