# apps/pantry-manager/main.py
# Run: uvicorn main:app --reload --port 8004

from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Field, Session, SQLModel, create_engine, select

# ── Database ──────────────────────────────────────────────────────────────────

engine = create_engine("sqlite:///./pantry.db", connect_args={"check_same_thread": False})

SHARED = Path(__file__).resolve().parent.parent.parent / "static"

# ── Models ────────────────────────────────────────────────────────────────────

class PantryItemBase(SQLModel):
    name:         str   = Field(description="Item name e.g. olive oil, pasta, eggs")
    quantity:     float = Field(description="Current quantity on hand")
    unit:         str   = Field(description="Unit of measurement e.g. liters, kg, count, cans")
    category:     str   = Field(description="Category e.g. dairy, produce, pantry, frozen, beverages")
    min_quantity: float = Field(default=1.0,
                                 description="Minimum quantity before considered low stock")

class PantryItem(PantryItemBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class PantryItemCreate(PantryItemBase):
    pass

class PantryItemUpdate(SQLModel):
    name:         Optional[str]   = Field(default=None)
    quantity:     Optional[float]  = Field(default=None, description="Set the new quantity on hand")
    unit:         Optional[str]   = Field(default=None)
    category:     Optional[str]   = Field(default=None)
    min_quantity: Optional[float]  = Field(default=None)

class PantryItemDeleted(SQLModel):
    deleted: int

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Pantry Manager")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def create_tables():
    SQLModel.metadata.create_all(engine)

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/items/low-stock", response_model=list[PantryItem], operation_id="list_low_stock",
         summary="Lists items whose current quantity is at or below their minimum threshold.")
def list_low_stock():
    with Session(engine) as s:
        items = s.exec(select(PantryItem)).all()
        return [i for i in items if i.quantity <= i.min_quantity]

@app.get("/items", response_model=list[PantryItem], operation_id="list_items",
         summary="Lists all pantry items, optionally filtered by category.")
def list_items(category: Optional[str] = None):
    with Session(engine) as s:
        q = select(PantryItem)
        if category:
            q = q.where(PantryItem.category == category)
        return s.exec(q).all()

@app.post("/items", response_model=PantryItem, status_code=201, operation_id="add_item",
          summary="Adds a new item to the pantry.")
def add_item(item: PantryItemCreate):
    with Session(engine) as s:
        row = PantryItem.model_validate(item)
        s.add(row); s.commit(); s.refresh(row)
        return row

@app.patch("/items/{item_id}", response_model=PantryItem, operation_id="update_item",
           summary="Updates a pantry item by id. Use this to adjust quantity after shopping or using items.")
def update_item(item_id: int, patch: PantryItemUpdate):
    with Session(engine) as s:
        row = s.get(PantryItem, item_id)
        if not row:
            raise HTTPException(404, f"Item {item_id} not found")
        for k, v in patch.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        s.add(row); s.commit(); s.refresh(row)
        return row

@app.delete("/items/{item_id}", response_model=PantryItemDeleted, operation_id="delete_item",
            summary="Removes an item from the pantry.")
def delete_item(item_id: int):
    with Session(engine) as s:
        row = s.get(PantryItem, item_id)
        if not row:
            raise HTTPException(404, f"Item {item_id} not found")
        s.delete(row); s.commit()
        return PantryItemDeleted(deleted=item_id)

# ── Static ────────────────────────────────────────────────────────────────────

app.mount("/shared", StaticFiles(directory=str(SHARED)), name="shared")
app.mount("/", StaticFiles(directory="static", html=True), name="static")
