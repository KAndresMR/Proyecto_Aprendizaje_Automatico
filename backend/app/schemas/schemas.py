from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict
from datetime import date, datetime

# ========================================
# PRODUCT SCHEMAS
# ========================================
class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    brand: str = Field(..., min_length=1, max_length=255)
    presentation: Optional[str] = None
    size: str = Field(..., min_length=1)
    barcode: Optional[str] = None
    description: Optional[str] = None


class ProductCreate(ProductBase):
    batch_number: Optional[str] = None
    expiry_date: Optional[date] = None
    manufacturing_date: Optional[date] = None
    price: Optional[float] = None


class ProductResponse(ProductBase):
    id: int
    normalized_size_value: Optional[float] = None
    normalized_size_unit: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # 🔹 CAMBIADO: ConfigDict en lugar de Config
    model_config = ConfigDict(from_attributes=True)


# ========================================
# BATCH SCHEMAS
# ========================================
class BatchBase(BaseModel):
    batch_number: Optional[str] = None
    expiry_date: Optional[date] = None
    manufacturing_date: Optional[date] = None
    price: Optional[float] = None
    stock_quantity: int = 0


class BatchCreate(BatchBase):
    product_id: int


class BatchResponse(BatchBase):
    id: int
    product_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ========================================
# IMAGE SCHEMAS
# ========================================
class ImageResponse(BaseModel):
    id: int
    image_type: str
    image_url: Optional[str] = None
    ocr_confidence: Optional[float] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ========================================
# OCR RESPONSE SCHEMAS
# ========================================
class OCRProduct(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    presentation: Optional[str] = None
    size: Optional[str] = None
    barcode: Optional[str] = None
    batch: Optional[str] = None
    expiry_date: Optional[str] = None
    price: Optional[float] = None


class OCRResult(BaseModel):
    raw_text: Dict
    confidence: float
    product: Dict
    missing_fields: List[str]
    duplicates: List[dict]
    is_duplicate: bool = False
    class Config:
        from_attributes = True

class ProcessingStatus(BaseModel):
    status: str
    message: str
    progress: int

# ========================================
# SAVE PRODUCT RESPONSE
# ========================================
class SaveProductResponse(BaseModel):
    id: int
    product: ProductResponse
    batch: Optional[BatchResponse] = None
    message: str