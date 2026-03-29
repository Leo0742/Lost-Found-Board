from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.item import ItemStatus
from app.schemas.item import ItemCreate, ItemRead, ItemUpdate, MatchResult
from app.services.item_service import ItemService

router = APIRouter(prefix="/api/items", tags=["items"])


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)) -> ItemRead:
    service = ItemService(db)
    return service.create_item(payload)


@router.get("", response_model=list[ItemRead])
def list_items(
    status: ItemStatus | None = Query(default=None),
    category: str | None = Query(default=None),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ItemRead]:
    service = ItemService(db)
    return service.list_items(status=status, category=category, q=q)


@router.get("/search", response_model=list[ItemRead])
def search_items(q: str = Query(min_length=1), db: Session = Depends(get_db)) -> list[ItemRead]:
    service = ItemService(db)
    return service.list_items(q=q)


@router.get("/{item_id}", response_model=ItemRead)
def get_item(item_id: int, db: Session = Depends(get_db)) -> ItemRead:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.patch("/{item_id}", response_model=ItemRead)
def update_item(item_id: int, payload: ItemUpdate, db: Session = Depends(get_db)) -> ItemRead:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return service.update_item(item, payload)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db)) -> None:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    service.delete_item(item)


@router.get("/matches/{item_id}", response_model=list[MatchResult])
def get_matches(item_id: int, db: Session = Depends(get_db)) -> list[MatchResult]:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return service.matches_for_item(item)
