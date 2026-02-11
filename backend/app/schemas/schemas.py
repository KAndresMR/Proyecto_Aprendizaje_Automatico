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
# OCR RESPONSE SCHEMAS
# ========================================


class OCRResult(BaseModel):
    confidence: float 
    product: Dict
    ocr_raw: Dict[str, str] 
    missing_fields: List[str]
    duplicates: List[Dict]
    is_duplicate: bool = False
    
    class Config:
        from_attributes = True

# ========================================
# SAVE PRODUCT RESPONSE
# ========================================
class SaveProductResponse(BaseModel):
    id: int
    product: ProductResponse
    batch: Optional[BatchResponse] = None
    message: str