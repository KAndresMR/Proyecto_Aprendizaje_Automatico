"""
Create database tables from SQLAlchemy models.
"""

import sys
import os
import asyncio

# Add project root to PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

from database.connection import get_engine
from database.models.product_stock import Base as ProductStockBase
from database.models.product_image import ProductImage  # noqa: F401


async def create_tables():
    engine = get_engine()

    async with engine.begin() as conn:
        await conn.run_sync(ProductStockBase.metadata.create_all)

    print("✅ Tablas creadas correctamente.")


if __name__ == "__main__":
    asyncio.run(create_tables())
