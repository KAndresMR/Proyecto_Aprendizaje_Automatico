from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
from sqlalchemy import select
from app.schemas import (
    ProductCreate, ProductResponse, OCRResult, 
    SaveProductResponse, BatchResponse
)
from app.models import Product, ProductBatch, ProductImage, OCRLog
from app.services.ocr_service import ocr_service
from app.services.image_service import image_service
from app.services.normalizer_service import normalizer_service
from app.services.deduplicator_service import deduplicator_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/inventory", tags=["Inventory"])

@router.post("/from-images", response_model=OCRResult)
async def process_images_from_camera(
    photo_0: Optional[UploadFile] = File(None),
    photo_1: Optional[UploadFile] = File(None),
    photo_2: Optional[UploadFile] = File(None),
    photo_3: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Procesar imágenes capturadas desde la cámara.
    Ejecuta OCR, normalización y detección de duplicados.
    """
    try:
        logger.info("📸 Iniciando procesamiento de imágenes...")
        
        # Recopilar archivos subidos
        files = []
        image_types = []
        
        if photo_0:
            files.append(photo_0)
            image_types.append("front")
        if photo_1:
            files.append(photo_1)
            image_types.append("left")
        if photo_2:
            files.append(photo_2)
            image_types.append("right")
        if photo_3:
            files.append(photo_3)
            image_types.append("back")
        
        if not files:
            raise HTTPException(status_code=400, detail="No se recibieron imágenes")
        
        # 1. Guardar imágenes
        logger.info("💾 Guardando imágenes...")
        saved_images = image_service.save_multiple_images(files, image_types)
        
        # 2. Ejecutar OCR en todas las imágenes
        logger.info("🔍 Ejecutando OCR...")
        ocr_data = ocr_service.extract_from_multiple_images(saved_images)
        
        # Guardar log de OCR
        ocr_log = OCRLog(
            image_path=",".join(saved_images.values()),
            raw_text=str(ocr_data),
            confidence=ocr_data["overall_confidence"],
            ocr_engine=ocr_service.engine
        )
        db.add(ocr_log)
        await db.commit()
        
        # 3. Normalizar y extraer información del producto
        logger.info("⚙️ Normalizando datos...")
        product_info = normalizer_service.extract_product_info(ocr_data)
        
        # 4. Detectar campos faltantes
        missing_fields = []
        required_fields = ["name", "brand", "size"]
        
        for field in required_fields:
            if not product_info.get(field):
                missing_fields.append(field)
        
        # 5. Buscar duplicados
        logger.info("🔍 Buscando productos similares...")
        duplicates = []
        
        if product_info.get("name") and product_info.get("brand"):
            # 🔹 CAMBIADO: await porque ahora es async
            duplicates = await deduplicator_service.find_similar_products(
                db=db,
                name=product_info["name"],
                brand=product_info["brand"],
                size=product_info.get("size", "")
            )
        
        logger.info("✅ Procesamiento completado")
        
        product_info.setdefault("presentation", None)
        product_info.setdefault("barcode", None)
        product_info.setdefault("batch", None)
        product_info.setdefault("expiry_date", None)
        product_info.setdefault("price", None)
        
        logger.info(
            "⬅️ Response OCRResult: confidence=%s, product=%s, missing=%s, duplicates=%d",
            ocr_data["overall_confidence"],
            product_info,
            missing_fields,
            len(duplicates)
        )
        
        logger.info("🔥 JUSTO ANTES DEL RETURN FINAL")

        
        return OCRResult(
            raw_text=ocr_data,
            confidence=ocr_data["overall_confidence"],
            product=product_info,
            missing_fields=missing_fields,
            duplicates=duplicates
        )
        
    except Exception as e:
        logger.error(f"❌ Error en procesamiento: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save", response_model=SaveProductResponse)
async def save_product(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Guardar producto en la base de datos.
    Crea el producto, batch e imágenes asociadas.
    """
    try:
        logger.info(f"💾 Guardando producto: {product_data.name}")
        
        # Normalizar tamaño
        normalized_value, normalized_unit = normalizer_service.normalize_size(
            product_data.size
        )
        
        # Crear producto
        new_product = Product(
            name=product_data.name,
            brand=product_data.brand,
            presentation=product_data.presentation,
            size=product_data.size,
            normalized_size_value=normalized_value,
            normalized_size_unit=normalized_unit,
            barcode=product_data.barcode,
            description=product_data.description
        )
        
        db.add(new_product)
        await db.flush()  # Para obtener el ID
        
        # Crear batch si hay información
        new_batch = None
        if any([
            product_data.batch_number,
            product_data.expiry_date,
            product_data.price
        ]):
            new_batch = ProductBatch(
                product_id=new_product.id,
                batch_number=product_data.batch_number,
                expiry_date=product_data.expiry_date,
                manufacturing_date=product_data.manufacturing_date,
                price=product_data.price
            )
            db.add(new_batch)
        
        await db.commit()
        await db.refresh(new_product)
        
        logger.info(f"✅ Producto guardado con ID: {new_product.id}")
        
        # 🔹 CAMBIADO: model_validate en lugar de from_orm
        return SaveProductResponse(
            id=new_product.id,
            product=ProductResponse.model_validate(new_product),
            batch=BatchResponse.model_validate(new_batch) if new_batch else None,
            message=f"Producto '{new_product.name}' registrado exitosamente"
        )
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error guardando producto: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products", response_model=List[ProductResponse])
async def get_all_products(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Obtener todos los productos"""
    stmt = (
        select(Product)
        .where(Product.is_active == True)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    products = result.scalars().all()
    return products


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtener un producto por ID"""
    stmt = select(Product).where(Product.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    return product