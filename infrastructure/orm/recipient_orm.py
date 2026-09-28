import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from infrastructure.orm.base import Base


class RecipientORM(Base):
    __tablename__ = "recipients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_code = Column(String(2), nullable=False)
    legal_name = Column(String(255), nullable=False)
    tax_id_type = Column(String(20), nullable=False)
    tax_id_value = Column(String(50), nullable=False)
    address = Column(Text, nullable=False)
    extra = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
