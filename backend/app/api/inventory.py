import logging
import asyncio
import time
import json

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import Response

from backend.app.core.database import get_db
from backend.app.schemas.schemas import (
    ProductCreate, ProductResponse, OCRResult, 
    SaveProductResponse, BatchResponse
)
from backend.app.models.models import Product, ProductBatch, OCRLog
from backend.app.services import (
    ocr_service,
    image_service,
    normalizer_service,
    deduplicator_service,
    ai_extractor_service,
    voice_service,
    vector_service
    
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.post("/from-images", response_model=OCRResult)
async def process_images_from_camera(
    photo_0: Optional[UploadFile] = File(None),
    photo_1: Optional[UploadFile] = File(None),
    photo_2: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Pipeline optimizado:
    1. Guardado paralelo
    2. OCR paralelo (con preprocesamiento interno)
    3. Normalización + Deduplicación en paralelo
    """
    try:
        logger.info("📸 Iniciando procesamiento optimizado...")
        start_total = time.time()
        
        # Recopilar archivos
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
        if not files:
            raise HTTPException(status_code=400, detail="No se recibieron imágenes")
        
        # 1️⃣ Guardar imágenes EN PARALELO
        logger.info("💾 Guardando imágenes...")
        start = time.time()
        saved_images = await image_service.save_multiple_images_async(files, image_types)
        logger.info(f"⏱️ Guardado: {time.time()-start:.2f}s")
        
        # 2️⃣ OCR PARALELO
        logger.info("🔍 Ejecutando OCR optimizado...")
        start = time.time()
        ocr_data = ocr_service.extract_from_multiple_images(saved_images)
        logger.info(f"⏱️ OCR: {time.time()-start:.2f}s")
        
        # Logs temporales
        logger.info("="*70)
        logger.info("🔍 DEBUG OCR DATA:")
        logger.info(f"Overall confidence: {ocr_data.get('overall_confidence', 'N/A')}")
        for img_type, data in ocr_data.get('images', {}).items():
            logger.info(f"  {img_type}: conf={data.get('confidence', 0):.2f}, text_len={len(data.get('text', ''))}")
        logger.info("="*70)
        # ----
        
        # 🔍 DEBUG - Ver estructura OCR
        logger.debug(f"OCR Data: {json.dumps(ocr_data, indent=2, ensure_ascii=False)[:500]}")
        
        # 3️⃣ EXTRACCIÓN CON IA
        logger.info("🤖 Extrayendo información con Gemini...")
        start = time.time()
        product_info = await asyncio.to_thread(
            ai_extractor_service.extract_product_info,
            ocr_data
        )
        
        # Logs temporales
        logger.info("="*70)
        logger.info("🔍 DEBUG PRODUCT INFO:")
        logger.info(f"Nombre: {product_info.get('name', 'N/A')}")
        logger.info(f"Marca: {product_info.get('brand', 'N/A')}")
        logger.info(f"Tamaño: {product_info.get('size', 'N/A')}")
        logger.info(f"Barcode: {product_info.get('barcode', 'N/A')}")
        logger.info(f"Extraído con: {product_info.get('_extracted_with', 'gemini')}")
        logger.info("="*70)
        # ----
        
        logger.info(f"⏱️ IA Extracción: {time.time()-start:.2f}s")
        
        # 🔍 DEBUG - Ver producto extraído
        logger.debug(f"Product Info: {json.dumps(product_info, indent=2, ensure_ascii=False)[:500]}")
        
        # 4️⃣ BUSCAR DUPLICADOS (con barcode primero)
        logger.info("🔍 Buscando duplicados...")
        duplicates = []
        
        if any([
            product_info.get("barcode"),
            product_info.get("name"),
            product_info.get("brand")
        ]):
            duplicates = await deduplicator_service.find_similar_products(
                db=db,
                name=product_info.get("name", ""),
                brand=product_info.get("brand", ""),
                barcode=product_info.get("barcode"),
                size=product_info.get("size", "")
            )
        
        # 5️⃣ SI HAY DUPLICADO EXACTO, RETORNAR EXISTENTE
        if duplicates and duplicates[0].get("similarity", 0) >= 0.95:
            logger.info(f"🔄 Producto duplicado detectado: {duplicates[0]['name']}")
            existing_id = duplicates[0]["id"]
            stmt = select(Product).where(Product.id == existing_id)
            result = await db.execute(stmt)
            product = result.scalar_one()
            
            batch_number = product_info.get("batch")

            stmt_batch = select(ProductBatch).where(
                ProductBatch.product_id == product.id,
                ProductBatch.batch_number == batch_number
            )

            result_batch = await db.execute(stmt_batch)
            existing_batch = result_batch.scalar_one_or_none()
            if existing_batch:
                # 🔁 Incrementar stock
                existing_batch.stock_quantity += 1
                await db.commit()
                batch = existing_batch
            else:
                # 🆕 Crear nuevo lote
                batch = ProductBatch(
                    product_id=product.id,
                    batch_number=batch_number,
                    expiry_date=product_info.get("expiry_date"),
                    manufacturing_date=product_info.get("manufacturing_date"),
                    price=product_info.get("price"),
                    stock_quantity=1
                )
                db.add(batch)
                await db.commit()
                await db.refresh(batch)
            
            return OCRResult(
                confidence=ocr_data["overall_confidence"],
                product={
                    "id": product.id,
                    "name": product.name,
                    "brand": product.brand,
                    "presentation": product.presentation,
                    "size": product.size,
                    "barcode": product.barcode,
                    "image_front": product.image_front,
                    "image_left": product.image_left,
                    "image_right": product.image_right,
                    # 👇 Datos reales desde ProductBatch
                    "batch": batch.batch_number,
                    "expiry_date": batch.expiry_date,
                    "price": batch.price,
                    "stock_quantity": batch.stock_quantity,
                },
                missing_fields=[],
                duplicates=duplicates,
                is_duplicate=True
            )
        
        # 6️⃣ PRODUCTO NUEVO: Agregar rutas de imágenes
        product_info["image_front"] = saved_images.get("front")
        product_info["image_left"] = saved_images.get("left")
        product_info["image_right"] = saved_images.get("right")
        
        # 7️⃣ DETECTAR CAMPOS FALTANTES
        required_fields = ["name", "brand", "size"]
        missing_required = [
            field for field in required_fields
            if not product_info.get(field)
        ]
        logger.info(f"⚠️ Campos faltantes detectados: {missing_required}")
        
        # GARANTIZAR campos obligatorios con valores por defecto
        if not product_info.get("name"):
            logger.error("❌ No se pudo extraer el nombre del producto")
            raise HTTPException(
                status_code=400,
                detail="No se pudo identificar el producto. Por favor, tome fotos más claras."
            )
        # NUEVO: Valores por defecto para campos NOT NULL en BD   
        if not product_info.get("brand"):
            product_info["brand"] = "Sin Marca"
            logger.warning("⚠️ Marca no detectada, usando 'Sin Marca'")

        if not product_info.get("size"):
            product_info["size"] = "N/A" 
            logger.warning("⚠️ Tamaño no detectado, usando 'N/A'")

        # 🔹 Crear objeto Product
        new_product = Product(
            name=product_info.get("name"),
            brand=product_info.get("brand"),
            presentation=product_info.get("presentation"),
            size=product_info.get("size"),
            barcode=product_info.get("barcode"),
            image_front=product_info.get("image_front"),
            image_left=product_info.get("image_left"),
            image_right=product_info.get("image_right"),
        )
        db.add(new_product)
        await db.commit()
        await db.refresh(new_product)
        
        # Guardar embedding
        try:
            vector_service.add_product(
                product_id=new_product.id,
                embedding_text = " ".join(
                    filter(None, [
                        new_product.name,
                        new_product.brand,
                        new_product.size,
                        new_product.presentation
                    ])
                )
            )
        except Exception as e:
            logger.warning(f"⚠️ No se pudo guardar embedding: {e}")
            
        new_batch = ProductBatch(
            product_id=new_product.id,
            batch_number=product_info.get("batch"),
            expiry_date=product_info.get("expiry_date"),
            manufacturing_date=product_info.get("manufacturing_date"),
            price=product_info.get("price"),
            stock_quantity=1  # o lo que definas por default
        )

        db.add(new_batch)
        await db.commit()
        await db.refresh(new_batch)
        
        # Defaults para campos opcionales
        for field in ["presentation", "barcode", "batch", "expiry_date", "price"]:
            product_info.setdefault(field, None)
        
        # 8️⃣ GUARDAR LOG
        formatted_ocr = json.dumps(ocr_data, indent=2, ensure_ascii=False)
        ocr_log = OCRLog(
            image_path=",".join(saved_images.values()),
            raw_text= formatted_ocr, # raw_text=str(ocr_data),
            confidence=ocr_data["overall_confidence"],
            ocr_engine=ocr_service.engine
        )
        # logger.info("OCR DATA:\n%s", formatted_ocr)
        db.add(ocr_log)
        await db.commit()
        
        total_time = time.time() - start_total
        logger.info(f"✅ Procesamiento completado en {total_time:.2f}s")
        logger.info(
            f"📊 Producto: {product_info.get('name', 'N/A')} | "
            f"Marca: {product_info.get('brand', 'N/A')} | "
            f"Tamaño: {product_info.get('size', 'N/A')} | "
            f"Duplicados: {len(duplicates)}"
        )
        
        return OCRResult(
            confidence=ocr_data["overall_confidence"],
            product={
                "id": new_product.id,
                "name": new_product.name,
                "brand": new_product.brand,
                "presentation": new_product.presentation,
                "size": new_product.size,
                "barcode": new_product.barcode,
                "batch": new_batch.batch_number,
                "expiry_date": str(new_batch.expiry_date) if new_batch.expiry_date else None,
                "price": float(new_batch.price) if new_batch.price else None,
                "image_front": new_product.image_front,
                "image_left": new_product.image_left,
                "image_right": new_product.image_right,
            },
            ocr_raw={
                "front": ocr_data["images"].get("front", {}).get("text", ""),
                "left": ocr_data["images"].get("left", {}).get("text", ""),
                "right": ocr_data["images"].get("right", {}).get("text", "")
            },
            missing_fields=missing_required,
            duplicates=duplicates,
            is_duplicate=False
        )
    except Exception as e:
        logger.error(f"❌ Error en procesamiento: {e}", exc_info=True)
        await db.rollback()
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


@router.post("/voice/confirm")
async def voice_confirmation(data: dict):
    """
    Generar confirmación por voz con ElevenLabs
    
    Recibe: {"product_name": "Coca Cola"}
    Retorna: Audio MP3 en bytes
    """
    product_name = data.get("product_name", "producto")
    
    text = f"Producto {product_name} registrado correctamente en el inventario"
    
    audio = voice_service.generate_audio(text)
    
    if audio:
        return Response(
            content=audio, 
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=confirmation.mp3"
            }
        )
    else:
        raise HTTPException(
            status_code=503, 
            detail="Servicio de voz no disponible"
        )