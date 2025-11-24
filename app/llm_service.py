import os
import json

from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain


def _build_chain():
    """
    Construye el chain de LangChain que usaremos para resumir las predicciones.
    """
    llm = ChatOpenAI(
        model_name=os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo"),
        temperature=0.3,
    )

    template = """
Eres un analista de inventario y demanda.

Te entrego un JSON con predicciones de demanda de varios productos.
Cada item tiene campos como: product_id, date, pred_quantity_sold, alert, etc.

JSON de predicciones:
{predictions_json}

Quiero que respondas en español, con este formato:

1. **Resumen general (2-3 frases)**
   - Explica si la demanda esperada es alta, normal o baja en general.
   - Menciona si hay muchos productos en estado CRITICO o ADVERTENCIA.

2. **Productos con riesgo (lista en viñetas)**
   - Para cada producto en estado CRITICO o ADVERTENCIA:
     - product_id
     - fecha
     - demanda estimada (pred_quantity_sold)
     - estado (CRITICO / ADVERTENCIA)
     - recomendación concreta de stock (ej: “aumentar reposición en X unidades”, “revisar precio”, etc.)

3. **Recomendaciones finales (2-3 bullets)**
   - Consejos generales de gestión de inventario basados en las predicciones.

Habla de forma clara, concreta y profesional.
No inventes productos ni campos que no existan en el JSON.
    """

    prompt = PromptTemplate(
        template=template,
        input_variables=["predictions_json"],
    )

    chain = LLMChain(llm=llm, prompt=prompt)
    return chain


# Construimos el chain una sola vez
_chain = _build_chain()


def generate_summary(predictions: list[dict]) -> str:
    """
    Recibe la lista de predicciones (lo que devuelve /predict)
    y retorna un texto con conclusiones en español.
    """
    predictions_json = json.dumps(predictions, ensure_ascii=False, indent=2)
    result = _chain.run(predictions_json=predictions_json)
    return result