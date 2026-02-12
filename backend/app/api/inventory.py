import logging
import asyncio
import time
import json

from datetime import datetime, date
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
    try:
        logger.info("📸 Iniciando procesamiento...")
        start_total = time.time()
        
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
        
        # Guardar imágenes
        logger.info("💾 Guardando imágenes...")
        start = time.time()
        saved_images = await image_service.save_multiple_images_async(files, image_types)
        logger.info(f"⏱️ Guardado: {time.time()-start:.2f}s")
        
        logger.info("🔍 Ejecutando OCR...")
        start = time.time()
        ocr_data = ocr_service.extract_from_multiple_images(saved_images)
        logger.info(f"⏱️ OCR: {time.time()-start:.2f}s")
        
        # 🔍 DEBUG - Ver estructura OCR
        logger.debug(f"OCR Data: {json.dumps(ocr_data, indent=2, ensure_ascii=False)[:500]}")
        
        
        # EXTRACCIÓN MULTIPLE
        # Opción 1: Usar Gemini (si falla → Mock)
        # Opción 2: Usar Llama (si falla → Mock)
        logger.info("🤖 Extrayendo información con IA...")
        logger.info(
            f"[AI] ▶ Iniciando extracción async | strategy=llama "
            f"| ocr_conf={ocr_data.get('overall_confidence', 'N/A')}"
        )
        start = time.time()
        product_info = await asyncio.to_thread(
            ai_extractor_service.extract_product_info,
            ocr_data,
            strategy = 'llama' ,
        )
        elapsed = time.time() - start
        logger.info(
            f"[AI] ✅ Extracción completada | strategy=llama "
            f"| tiempo_total={elapsed:.3f}s "
            f"| completeness={product_info.get('_completeness', 'N/A')}"
        )   
        
        logger.info(f"⏱️ IA Extracción: {time.time()-start:.2f}s")
        
        # 🔍 DEBUG - Ver producto extraído
        logger.debug(f"Product Info: {json.dumps(product_info, indent=2, ensure_ascii=False)[:500]}")
        
        # 4️⃣ BUSCAR DUPLICADOS
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

        # 5️⃣ DETERMINAR SI ES DUPLICADO REAL
        is_duplicate = False
        best_match = None

        if duplicates:
            best_match = duplicates[0]
            similarity = best_match.get("similarity", 0)
            match_type = best_match.get("match_type", "")
            
            # ✅ CRITERIOS DE DUPLICADO (más flexibles):
            # - Similarity >= 0.75 (75%) - umbral rebajado
            # - Match type debe indicar que es el mismo producto
            
            if similarity >= 0.75:
                # Tipos que SÍ son duplicados
                if match_type in ["barcode", "name_brand_size", "name_brand_no_size"]:
                    is_duplicate = True
                    logger.info(
                        f"🔄 DUPLICADO detectado: {best_match['name']} | "
                        f"Similarity: {similarity*100:.1f}% | Type: {match_type}"
                    )
                
                # Tipo que NO es duplicado (diferente presentación)
                elif match_type == "related_product":
                    logger.info(
                        f"ℹ️ Producto RELACIONADO (no duplicado): {best_match['name']} | "
                        f"Probablemente diferente presentación/tamaño"
                    )
                    is_duplicate = False
            else:
                logger.info(f"ℹ️ Similitud baja ({similarity*100:.1f}%), no es duplicado")

        # 6️⃣ SI ES DUPLICADO → GESTIONAR LOTES
        if is_duplicate and best_match:
            existing_id = best_match["id"]
            
            # Obtener producto existente
            stmt = select(Product).where(Product.id == existing_id)
            result = await db.execute(stmt)
            existing_product = result.scalar_one()
            
            # ============================================
            # GESTIÓN DE LOTES
            # ============================================
            batch_number = product_info.get("batch")
            
            # Si no hay número de lote, generar uno temporal
            if not batch_number:
                batch_number = f"AUTO-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                logger.warning(f"⚠️ No hay número de lote, usando: {batch_number}")
            
            # Buscar si ya existe este lote
            stmt_batch = select(ProductBatch).where(
                ProductBatch.product_id == existing_product.id,
                ProductBatch.batch_number == batch_number
            )
            
            result_batch = await db.execute(stmt_batch)
            existing_batch = result_batch.scalar_one_or_none()
            
            if existing_batch:
                # 🔁 LOTE EXISTENTE: Incrementar stock
                existing_batch.stock_quantity += 1
                await db.commit()
                await db.refresh(existing_batch)
                batch = existing_batch
                logger.info(
                    f"📦 Stock incrementado | Lote: {batch_number} | "
                    f"Nuevo stock: {batch.stock_quantity}"
                )
            else:
                # 🆕 NUEVO LOTE: Crear registro
                batch = ProductBatch(
                    product_id=existing_product.id,
                    batch_number=batch_number,
                    expiry_date=product_info.get("expiry_date"),
                    manufacturing_date=product_info.get("manufacturing_date"),
                    price=product_info.get("price"),
                    stock_quantity=1
                )
                db.add(batch)
                await db.commit()
                await db.refresh(batch)
                logger.info(f"🆕 Nuevo lote creado: {batch_number}")
            
            # ============================================
            # RETORNAR PRODUCTO EXISTENTE
            # ============================================
            return OCRResult(
                confidence=ocr_data["overall_confidence"],
                product={
                    "id": existing_product.id,
                    "name": existing_product.name,
                    "brand": existing_product.brand,
                    "presentation": existing_product.presentation,
                    "size": existing_product.size,
                    "barcode": existing_product.barcode,
                    "category": existing_product.category,
                    "image_front": existing_product.image_front,
                    "image_left": existing_product.image_left,
                    "image_right": existing_product.image_right,
                    # 👇 Datos del LOTE ACTUAL
                    "batch": batch.batch_number,
                    "expiry_date": str(batch.expiry_date) if batch.expiry_date else None,
                    "manufacturing_date": str(batch.manufacturing_date) if batch.manufacturing_date else None,
                    "price": float(batch.price) if batch.price else None,
                    "stock_quantity": batch.stock_quantity,
                    
                    
                    
                },
                ocr_raw={
                    "front": ocr_data["images"].get("front", {}).get("text", ""),
                    "left": ocr_data["images"].get("left", {}).get("text", ""),
                    "right": ocr_data["images"].get("right", {}).get("text", "")
                },
                missing_fields=[],
                duplicates=duplicates,
                is_duplicate=True
            )

        # 7️⃣ SI NO ES DUPLICADO → Continuar con creación de producto nuevo...
        
        # ============================================================================
        # 7️⃣ SI NO ES DUPLICADO → CREAR PRODUCTO NUEVO
        # ============================================================================

        logger.info("🆕 Creando producto nuevo...")

        # ────────────────────────────────────────────────────────────────────────
        # 7.1 - AGREGAR RUTAS DE IMÁGENES
        # ────────────────────────────────────────────────────────────────────────
        product_info["image_front"] = saved_images.get("front")
        product_info["image_left"] = saved_images.get("left")
        product_info["image_right"] = saved_images.get("right")

        # Verificar que al menos tengamos una imagen
        if not any(saved_images.values()):
            logger.error("❌ No se guardaron imágenes del producto")
            raise HTTPException(
                status_code=400,
                detail="Error al procesar las imágenes. Por favor, intente nuevamente."
            )

        # ────────────────────────────────────────────────────────────────────────
        # 7.2 - VALIDAR CAMPOS OBLIGATORIOS
        # ────────────────────────────────────────────────────────────────────────
        required_fields = ["name", "brand", "size"]
        missing_required = [
            field for field in required_fields
            if not product_info.get(field)
        ]

        if missing_required:
            logger.warning(f"⚠️ Campos obligatorios faltantes: {missing_required}")

        # GARANTIZAR campo NAME (crítico)
        if not product_info.get("name"):
            logger.error("❌ No se pudo extraer el nombre del producto")
            raise HTTPException(
                status_code=400,
                detail="No se pudo identificar el producto. Por favor, tome fotos más claras del producto."
            )

        # GARANTIZAR campos NOT NULL con valores por defecto
        if not product_info.get("brand"):
            product_info["brand"] = "Sin Marca"
            logger.warning("⚠️ Marca no detectada, usando 'Sin Marca'")

        if not product_info.get("size"):
            product_info["size"] = "N/A"
            logger.warning("⚠️ Tamaño no detectado, usando 'N/A'")

        # ────────────────────────────────────────────────────────────────────────
        # 7.3 - CREAR REGISTRO DE PRODUCTO
        # ────────────────────────────────────────────────────────────────────────
        new_product = Product(
            name=product_info.get("name"),
            brand=product_info.get("brand"),
            presentation=product_info.get("presentation"),
            size=product_info.get("size"),
            category=product_info.get("category"),
            barcode=product_info.get("barcode"),
            image_front=product_info.get("image_front"),
            image_left=product_info.get("image_left"),
            image_right=product_info.get("image_right"),
        )

        db.add(new_product)
        await db.commit()
        await db.refresh(new_product)

        logger.info(f"✅ Producto creado con ID: {new_product.id}")

        # ────────────────────────────────────────────────────────────────────────
        # 7.4 - GUARDAR EMBEDDING VECTORIAL (para búsqueda semántica)
        # ────────────────────────────────────────────────────────────────────────
        try:
            embedding_text = " ".join(
                filter(None, [
                    new_product.name,
                    new_product.brand,
                    new_product.size,
                    new_product.presentation,
                    new_product.category
                ])
            )
            
            vector_service.add_product(
                product_id=new_product.id,
                embedding_text=embedding_text
            )
            logger.info("✅ Embedding guardado correctamente")
            
        except Exception as e:
            logger.warning(f"⚠️ No se pudo guardar embedding: {e}")
            # No es crítico, continuamos

        # ────────────────────────────────────────────────────────────────────────
        # 7.5 - CREAR PRIMER LOTE DEL PRODUCTO
        # ────────────────────────────────────────────────────────────────────────
        batch_number = product_info.get("batch")

        # Si no hay número de lote, generar uno automático
        if not batch_number:
            batch_number = f"AUTO-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            logger.warning(f"⚠️ Lote no detectado, generando automático: {batch_number}")

        new_batch = ProductBatch(
            product_id=new_product.id,
            batch_number=batch_number,
            expiry_date=product_info.get("expiry_date"),
            manufacturing_date=product_info.get("manufacturing_date"),
            price=product_info.get("price"),
            stock_quantity=1  # Stock inicial
        )

        db.add(new_batch)
        await db.commit()
        await db.refresh(new_batch)

        logger.info(f"✅ Lote creado: {batch_number} | Stock: 1")

        # ────────────────────────────────────────────────────────────────────────
        # 7.6 - VALIDAR FECHA DE VENCIMIENTO (alerta si está vencido)
        # ────────────────────────────────────────────────────────────────────────
        if new_batch.expiry_date:
            if new_batch.expiry_date < date.today():
                logger.warning(
                    f"⚠️ PRODUCTO VENCIDO | "
                    f"Vencimiento: {new_batch.expiry_date} | "
                    f"Producto: {new_product.name}"
                )

        # ────────────────────────────────────────────────────────────────────────
        # 7.7 - DETECTAR TODOS LOS CAMPOS FALTANTES (para reporte)
        # ────────────────────────────────────────────────────────────────────────
        all_fields = [
            "name", "brand", "size", "category", "presentation",
            "barcode", "batch", "expiry_date", "price"
        ]

        missing_all_fields = [
            field for field in all_fields
            if not product_info.get(field) or product_info.get(field) in ["N/A", "Sin Marca"]
        ]

        if missing_all_fields:
            logger.info(f"ℹ️ Campos sin detectar: {missing_all_fields}")

        # ────────────────────────────────────────────────────────────────────────
        # 8️⃣ GUARDAR LOG DE OCR
        # ────────────────────────────────────────────────────────────────────────
        formatted_ocr = json.dumps(ocr_data, indent=2, ensure_ascii=False)

        ocr_log = OCRLog(
            image_path=",".join(saved_images.values()),
            raw_text=formatted_ocr,  # JSON formateado para debugging
            confidence=ocr_data["overall_confidence"],
            ocr_engine=ocr_service.engine
        )

        db.add(ocr_log)
        await db.commit()

        logger.info("✅ Log de OCR guardado")

        # ────────────────────────────────────────────────────────────────────────
        # 9️⃣ MÉTRICAS FINALES Y RESPUESTA
        # ────────────────────────────────────────────────────────────────────────
        total_time = time.time() - start_total

        logger.info(
            f"✅ PROCESAMIENTO COMPLETO | Tiempo: {total_time:.2f}s\n"
            f"   📦 Producto: {new_product.name}\n"
            f"   🏷️  Marca: {new_product.brand}\n"
            f"   📏 Tamaño: {new_product.size}\n"
            f"   🔖 Categoría: {new_product.category or 'N/A'}\n"
            f"   📊 Confianza OCR: {ocr_data['overall_confidence'] * 100:.2f}%\n"
            f"   🔍 Duplicados encontrados: {len(duplicates)}\n"
            f"   ⚠️  Campos faltantes: {len(missing_all_fields)}"
        )

        return OCRResult(
            confidence=ocr_data["overall_confidence"],
            product={
                "id": new_product.id,
                "name": new_product.name,
                "brand": new_product.brand,
                "presentation": new_product.presentation,
                "size": new_product.size,
                "category": new_product.category,
                "barcode": new_product.barcode,
                # Datos del lote
                "batch": new_batch.batch_number,
                "expiry_date": str(new_batch.expiry_date) if new_batch.expiry_date else None,
                "manufacturing_date": str(new_batch.manufacturing_date) if new_batch.manufacturing_date else None,
                "price": float(new_batch.price) if new_batch.price else None,
                "stock_quantity": new_batch.stock_quantity,
                # Imágenes
                "image_front": new_product.image_front,
                "image_left": new_product.image_left,
                "image_right": new_product.image_right,
            },
            ocr_raw={
                "front": ocr_data["images"].get("front", {}).get("text", ""),
                "left": ocr_data["images"].get("left", {}).get("text", ""),
                "right": ocr_data["images"].get("right", {}).get("text", "")
            },
            missing_fields=missing_all_fields,
            duplicates=duplicates,
            is_duplicate=False
        )

        # ============================================================================
        # MANEJO DE ERRORES GLOBAL
        # ============================================================================
    except Exception as e:
        logger.error(f"❌ Error crítico en procesamiento: {e}", exc_info=True)
        await db.rollback()
            
        # Proporcionar error más descriptivo al usuario
        error_detail = str(e)
        if "unique constraint" in error_detail.lower():
            error_detail = "El producto ya existe en el sistema"
        elif "foreign key" in error_detail.lower():
            error_detail = "Error de relación en base de datos"
            
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el producto: {error_detail}"
        )


@router.post("/save", response_model=SaveProductResponse)
async def save_product(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        existing_product = None

        # 🔍 Verificar si ya existe por barcode
        if product_data.barcode:
            stmt = select(Product).where(
                Product.barcode == product_data.barcode
            )
            result = await db.execute(stmt)
            existing_product = result.scalar_one_or_none()

        # 🟢 Si existe → reutilizar
        if existing_product:
            logger.info("🔁 Producto ya existe, reutilizando registro")
            product = existing_product

        # 🆕 Si no existe → crear nuevo
        else:
            normalized_value, normalized_unit = normalizer_service.normalize_size(
                product_data.size
            )

            product = Product(
                name=product_data.name,
                brand=product_data.brand,
                presentation=product_data.presentation,
                size=product_data.size,
                normalized_size_value=normalized_value,
                normalized_size_unit=normalized_unit,
                barcode=product_data.barcode,
                description=product_data.description
            )

            db.add(product)
            await db.flush()  # obtener ID

            logger.info(f"🆕 Producto creado con ID: {product.id}")

        # 📦 Crear batch si hay datos
        new_batch = None
        if any([
            product_data.batch_number,
            product_data.expiry_date,
            product_data.price
        ]):
            new_batch = ProductBatch(
                product_id=product.id,  # 👈 IMPORTANTE
                batch_number=product_data.batch_number,
                expiry_date=product_data.expiry_date,
                manufacturing_date=product_data.manufacturing_date,
                price=product_data.price,
                stock_quantity=1
            )
            db.add(new_batch)

        await db.commit()
        await db.refresh(product)

        logger.info(f"✅ Guardado exitoso | product_id={product.id}")

        return SaveProductResponse(
            id=product.id,
            product=ProductResponse.model_validate(product),
            batch=BatchResponse.model_validate(new_batch) if new_batch else None,
            message=f"Producto '{product.name}' procesado correctamente"
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error guardando producto: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error guardando producto")


@router.get("/products", response_model=List[ProductResponse])
async def get_all_products(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
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
    stmt = select(Product).where(Product.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    return product


@router.post("/voice/confirm")
async def voice_confirmation(data: dict):
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