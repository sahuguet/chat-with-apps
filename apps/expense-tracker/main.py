# apps/expense-tracker/main.py
# Run: uvicorn main:app --reload --port 8001

from datetime import date
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Field, Session, SQLModel, create_engine, select

# ── Database ──────────────────────────────────────────────────────────────────

engine = create_engine("sqlite:///./expenses.db", connect_args={"check_same_thread": False})

SHARED = Path(__file__).resolve().parent.parent.parent / "static"

# ── Models ────────────────────────────────────────────────────────────────────

class ExpenseBase(SQLModel):
    description: str  = Field(description="What the expense was for")
    amount:      float = Field(description="Amount in dollars")
    category:    str  = Field(description="Category e.g. food, transport, utilities")
    date:        str  = Field(default_factory=lambda: date.today().isoformat(),
                               description="ISO date string (YYYY-MM-DD), defaults to today")

class Expense(ExpenseBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseUpdate(SQLModel):
    description: Optional[str]   = Field(default=None)
    amount:      Optional[float]  = Field(default=None)
    category:    Optional[str]   = Field(default=None)
    date:        Optional[str]   = Field(default=None)

class ExpenseDeleted(SQLModel):
    deleted: int

class Summary(SQLModel):
    by_category: dict = Field(description="Total spend per category")
    total:        float = Field(description="Grand total across all expenses")

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Expense Tracker")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def create_tables():
    SQLModel.metadata.create_all(engine)

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/expenses/summary", response_model=Summary, operation_id="get_expense_summary",
         summary="Returns total spend grouped by category, plus a grand total.")
def get_expense_summary():
    with Session(engine) as s:
        expenses = s.exec(select(Expense)).all()
        by_cat: dict[str, float] = {}
        for e in expenses:
            by_cat[e.category] = round(by_cat.get(e.category, 0) + e.amount, 2)
        return Summary(by_category=by_cat, total=round(sum(by_cat.values()), 2))

@app.get("/expenses", response_model=list[Expense], operation_id="list_expenses",
         summary="Lists all expenses, optionally filtered by category.")
def list_expenses(category: Optional[str] = None):
    with Session(engine) as s:
        q = select(Expense)
        if category:
            q = q.where(Expense.category == category)
        return s.exec(q).all()

@app.post("/expenses", response_model=Expense, status_code=201, operation_id="add_expense",
          summary="Records a new expense.")
def add_expense(expense: ExpenseCreate):
    with Session(engine) as s:
        row = Expense.model_validate(expense)
        s.add(row); s.commit(); s.refresh(row)
        return row

@app.patch("/expenses/{expense_id}", response_model=Expense, operation_id="update_expense",
           summary="Updates an existing expense by id.")
def update_expense(expense_id: int, patch: ExpenseUpdate):
    with Session(engine) as s:
        row = s.get(Expense, expense_id)
        if not row:
            raise HTTPException(404, f"Expense {expense_id} not found")
        for k, v in patch.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        s.add(row); s.commit(); s.refresh(row)
        return row

@app.delete("/expenses/{expense_id}", response_model=ExpenseDeleted, operation_id="delete_expense",
            summary="Deletes an expense by id.")
def delete_expense(expense_id: int):
    with Session(engine) as s:
        row = s.get(Expense, expense_id)
        if not row:
            raise HTTPException(404, f"Expense {expense_id} not found")
        s.delete(row); s.commit()
        return ExpenseDeleted(deleted=expense_id)

# ── Static ────────────────────────────────────────────────────────────────────

app.mount("/shared", StaticFiles(directory=str(SHARED)), name="shared")
app.mount("/", StaticFiles(directory="static", html=True), name="static")
