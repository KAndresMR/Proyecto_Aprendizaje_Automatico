"""
Async seed script for products and product images.

Loads products and images from the folder:
imagenes_productos/
"""

import sys
import os
import asyncio

# --------------------------------------------------
# Add project root to PYTHONPATH
# --------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

# --------------------------------------------------
# Imports from project
# --------------------------------------------------
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from database.connection import get_engine
from database.models.product_stock import ProductStock
from database.models.product_image import ProductImage


# --------------------------------------------------
# Config
# --------------------------------------------------
BASE_IMAGE_PATH = "imagenes_productos"


# --------------------------------------------------
# Seed logic
# --------------------------------------------------
async def seed_products() -> None:
    engine = get_engine()

    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        try:
            for product_folder in os.listdir(BASE_IMAGE_PATH):
                product_path = os.path.join(BASE_IMAGE_PATH, product_folder)

                if not os.path.isdir(product_path):
                    continue

                product_code = product_folder.lower()

                # ------------------------------------------
                # Check if product exists
                # ------------------------------------------
                result = await session.execute(
                    select(ProductStock).where(ProductStock.product_id == product_code)
                )
                product = result.scalar_one_or_none()

                if not product:
                    product = ProductStock(
                        product_id=product_code,
                        product_name=product_folder.replace("_", " ").title(),
                        supplier_id="SUP-001",
                        supplier_name="Proveedor Demo",
                        quantity_on_hand=100,
                        quantity_reserved=0,
                        quantity_available=100,
                        unit_cost=1.00,
                        total_value=100.00,
                        warehouse_location="MAIN",
                    )
                    session.add(product)
                    await session.flush()  # 🔑 genera product.id

                # ------------------------------------------
                # Insert images
                # ------------------------------------------
                for image_file in os.listdir(product_path):
                    image_type = None

                    if "front" in image_file:
                        image_type = "front"
                    elif "side_left" in image_file:
                        image_type = "side_left"
                    elif "side_right" in image_file:
                        image_type = "side_right"

                    if not image_type:
                        continue

                    image = ProductImage(
                        product_stock_id=product.id,
                        image_type=image_type,
                        image_path=os.path.join(product_path, image_file),
                    )
                    session.add(image)

            await session.commit()
            print("✅ Productos e imágenes cargados correctamente.")

        except Exception as e:
            await session.rollback()
            print("❌ Error durante el seeding:")
            print(e)


# --------------------------------------------------
# Entry point
# --------------------------------------------------
if __name__ == "__main__":
    asyncio.run(seed_products())
