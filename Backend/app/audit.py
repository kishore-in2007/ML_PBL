from sqlalchemy.orm import Session
from fastapi import Request

from app import models


def log_action(
    db: Session,
    user_id: str | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    detail: str | None = None,
    request: Request | None = None,
):
    """Writes an immutable audit trail entry. Called on every data access/mutation."""
    entry = models.AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        ip_address=request.client.host if request and request.client else None,
    )
    db.add(entry)
    db.commit()
