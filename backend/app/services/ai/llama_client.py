from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate

class LlamaClient:
    def __init__(self):
        self.llm = Ollama(model="llama3.2")
        
        self.prompt = PromptTemplate(
            input_variables=["ocr_text"],
            template="""Extrae información de este producto:

{ocr_text}

Responde en JSON:
{{"nombre": "...", "marca": "...", "tamano": "..."}}
"""
        )
    
    def extract(self, ocr_text):
        chain = self.prompt | self.llm
        response = chain.invoke({"ocr_text": ocr_text})
        return json.loads(response)