from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.core.database import Base

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    brand = Column(String(255), nullable=False, index=True)
    presentation = Column(String(100))
    size = Column(String(50), nullable=False)
    category = Column(String, nullable=True)
    normalized_size_value = Column(Float)  # Valor normalizado en unidad base
    normalized_size_unit = Column(String(10))  # g, ml, etc.
    barcode = Column(String(50), unique=True, index=True)
    description = Column(Text)
    
    # Rutas de imágenes
    image_front = Column(String, nullable=True)
    image_left = Column(String, nullable=True)
    image_right = Column(String, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relaciones
    batches = relationship("ProductBatch", back_populates="product")

class ProductBatch(Base):
    __tablename__ = "product_batches"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    batch_number = Column(String(100))
    expiry_date = Column(Date)
    manufacturing_date = Column(Date)
    price = Column(Float)
    stock_quantity = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    product = relationship("Product", back_populates="batches")


class OCRLog(Base):
    __tablename__ = "ocr_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    image_path = Column(String(500))
    raw_text = Column(Text)
    confidence = Column(Float)
    processing_time = Column(Float)  # segundos
    ocr_engine = Column(String(50))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())