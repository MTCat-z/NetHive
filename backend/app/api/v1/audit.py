"""
审计日志查询路由（仅管理员）
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.core.auth import require_admin
from app.core.database import get_session
from app.models.user import AuditLog, AuditLogRead, User

router = APIRouter()


@router.get("", summary="审计日志列表")
def list_audit_logs(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    username: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    q = select(AuditLog).order_by(AuditLog.created_at.desc())
    if username:
        q = q.where(AuditLog.username == username)
    if action:
        q = q.where(AuditLog.action == action)
    if resource_type:
        q = q.where(AuditLog.resource_type == resource_type)

    total = len(session.exec(select(AuditLog)).all())
    items = session.exec(q.offset((page - 1) * size).limit(size)).all()
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [AuditLogRead.model_validate(log) for log in items],
    }
