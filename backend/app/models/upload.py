import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Text, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DataUpload(Base):
    __tablename__ = "data_uploads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Upload details
    file_type: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # 'messages', 'connections'
    filename: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    records_processed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamp
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<DataUpload {self.file_type} - {self.uploaded_at}>"
