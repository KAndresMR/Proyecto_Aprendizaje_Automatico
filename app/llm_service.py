import os
import json
from dotenv import load_dotenv
import openai
from langchain.prompts import ChatPromptTemplate

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# ---------------------------
# Prompt template (LangChain)
# ---------------------------
prompt = ChatPromptTemplate.from_messages([
    ("system",
     "Eres un analista experto en ventas y stock. "
     "Genera informes claros, profesionales y concisos."),
    
    ("human",
    """
    Genera un informe basado en estas predicciones:

    {predictions_json}

    Requisitos:
    - Resumen general breve
    - Productos CRÍTICOS
    - Riesgos identificados
    - Recomendaciones claras y accionables
    """
    )
])

def generate_summary(predictions):
    # Convertimos predicciones a JSON bonito
    predictions_json = json.dumps(predictions, indent=2)

    try:
        # 🚀 LangChain SOLO para formatear el texto
        formatted = prompt.format(
            predictions_json=predictions_json
        )

        # En esta versión, formatted es un string.
        formatted_text = str(formatted)

        # Construimos mensajes para OpenAI clásico
        messages = [
            {
                "role": "system",
                "content": "Eres un analista experto en ventas y stock. Genera informes claros, profesionales y concisos."
            },
            {
                "role": "user",
                "content": formatted_text
            }
        ]

        # Llamada OpenAI API antigua
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages
        )

        return response["choices"][0]["message"]["content"]

    except Exception as e:
        print("\n================ LLM ERROR ================")
        print(e)
        print("===========================================\n")
        return "Error generando resumen LLM."