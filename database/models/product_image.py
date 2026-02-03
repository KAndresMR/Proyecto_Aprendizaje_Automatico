"""
ProductImage SQLAlchemy Model.

Stores product images and extracted metadata (OCR-ready).
"""

from datetime import datetime
from uuid import UUID
from sqlalchemy import text
from sqlalchemy import ForeignKey
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.product_stock import Base


class ProductImage(Base):
    __tablename__ = "product_images"
    __table_args__ = {"schema": "public"}

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    product_stock_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.product_stocks.id"),
        nullable=False,
    )

    image_type: Mapped[str] = mapped_column(
        Enum("front", "side_left", "side_right", name="image_type_enum"),
        nullable=False,
    )

    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
