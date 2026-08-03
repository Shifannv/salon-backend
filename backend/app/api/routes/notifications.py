from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import DeviceToken, Notification, Profile
from app.schemas.common import Message
from app.schemas.notification import DeviceTokenIn, DeviceTokenOut, NotificationOut

router = APIRouter()


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    user: Profile = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Notification]:
    return db.scalars(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
    ).all()


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: str,
    user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Notification:
    notification = db.get(Notification, notification_id)
    if not notification or notification.user_id != user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.read = True
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/devices", response_model=DeviceTokenOut)
def register_device(
    payload: DeviceTokenIn,
    user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceToken:
    device = db.scalar(select(DeviceToken).where(DeviceToken.token == payload.token))
    if device:
        device.user_id = user.id
        device.platform = payload.platform or device.platform
        device.device_name = payload.device_name or device.device_name
        device.is_active = True
    else:
        device = DeviceToken(user_id=user.id, **payload.model_dump())
        db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.delete("/devices/{token}", response_model=Message)
def deactivate_device(
    token: str,
    user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Message:
    device = db.scalar(select(DeviceToken).where(DeviceToken.token == token, DeviceToken.user_id == user.id))
    if device:
        device.is_active = False
        db.commit()
    return Message(message="Device token deactivated")

