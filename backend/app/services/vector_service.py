from chromadb import Client
from chromadb.config import Settings

class VectorService:
    def __init__(self):
        self.client = Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory="./chroma_db"
        ))
        self.collection = self.client.create_collection("products")
    
    def add_product_embedding(self, product_id, text):
        """Guardar embedding de producto"""
        self.collection.add(
            documents=[text],
            ids=[str(product_id)]
        )
    
    def search_similar(self, query_text, top_k=5):
        """Buscar productos similares por embeddings"""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=top_k
        )
        return results