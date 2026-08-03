from math import asin, cos, radians, sin, sqrt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models import Salon, Service
from app.schemas.salon import SalonListItem, SalonOut, ServiceOut

router = APIRouter()


def distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return round(radius * 2 * asin(sqrt(a)), 2)


@router.get("", response_model=list[SalonListItem])
def list_salons(
    q: str | None = None,
    city: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    radius_km: float | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
) -> list[SalonListItem]:
    stmt = (
        select(Salon)
        .where(Salon.is_active.is_(True), Salon.profile_completed.is_(True))
        .options(selectinload(Salon.images), selectinload(Salon.services))
    )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Salon.name.ilike(like), Salon.city.ilike(like), Salon.address.ilike(like)))
    if city:
        stmt = stmt.where(Salon.city.ilike(f"%{city}%"))

    items: list[SalonListItem] = []
    for salon in db.scalars(stmt).all():
        dist = None
        if lat is not None and lng is not None and salon.lat is not None and salon.lng is not None:
            dist = distance_km(lat, lng, salon.lat, salon.lng)
            if radius_km is not None and dist > radius_km:
                continue
        main_image = next((image.url for image in salon.images if image.is_main), None)
        starting_price = min((service.price for service in salon.services if service.is_active), default=None)
        items.append(
            SalonListItem(
                id=salon.id,
                name=salon.name,
                address=salon.address,
                city=salon.city,
                image_url=main_image,
                distance_km=dist,
                starting_price=starting_price,
            )
        )
    return sorted(items, key=lambda row: row.distance_km if row.distance_km is not None else 999999)


@router.get("/{salon_id}", response_model=SalonOut)
def get_salon(salon_id: str, db: Session = Depends(get_db)) -> Salon:
    salon = db.scalar(
        select(Salon)
        .where(Salon.id == salon_id, Salon.is_active.is_(True), Salon.profile_completed.is_(True))
        .options(selectinload(Salon.images))
    )
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    return salon


@router.get("/{salon_id}/services", response_model=list[ServiceOut])
def salon_services(salon_id: str, db: Session = Depends(get_db)) -> list[Service]:
    return db.scalars(
        select(Service).where(Service.salon_id == salon_id, Service.is_active.is_(True))
    ).all()


@router.get("/qr/{qr_token}", response_model=SalonOut)
def get_salon_by_qr(qr_token: str, db: Session = Depends(get_db)) -> Salon:
    salon = db.scalar(
        select(Salon)
        .where(Salon.qr_token == qr_token, Salon.is_active.is_(True), Salon.profile_completed.is_(True))
        .options(selectinload(Salon.images))
    )
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    return salon

