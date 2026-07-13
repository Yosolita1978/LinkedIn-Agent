import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AppSetting(Base):
    """
    Singleton table holding user-configurable dashboard settings.

    There is only ever one row. The route layer reads "the first row" and
    creates a default one if the table is empty (get-or-create), so the
    frontend never has to worry about whether the row exists yet.
    """

    __tablename__ = "app_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Personal weekly target for connection requests. Drives the "Weekly cap"
    # progress meter on the Today dashboard. User-settable; defaults to 25.
    weekly_request_cap: Mapped[int] = mapped_column(
        Integer, nullable=False, default=25
    )

    # Persona fields, editable from the Settings UI. NULL means "fall back to the
    # matching PERSONA_* value in .env" — so a fresh row behaves exactly like the
    # env-only config until the user overrides a field here.
    persona_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    persona_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    persona_location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    persona_bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    persona_interests: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<AppSetting weekly_request_cap={self.weekly_request_cap}>"
