# apps/personal-crm/main.py
# Run: uvicorn main:app --reload --port 8003

from datetime import date, timedelta
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Field, Session, SQLModel, create_engine, select

# ── Database ──────────────────────────────────────────────────────────────────

engine = create_engine("sqlite:///./crm.db", connect_args={"check_same_thread": False})

SHARED = Path(__file__).resolve().parent.parent.parent / "static"

# ── Models ────────────────────────────────────────────────────────────────────

class ContactBase(SQLModel):
    name:           str            = Field(description="Full name")
    email:          Optional[str]  = Field(default=None, description="Email address")
    phone:          Optional[str]  = Field(default=None, description="Phone number")
    notes:          Optional[str]  = Field(default=None, description="General notes about this person")
    last_contacted: Optional[str]  = Field(default=None, description="ISO date of last contact (YYYY-MM-DD)")

class Contact(ContactBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class ContactCreate(ContactBase):
    pass

class ContactUpdate(SQLModel):
    name:           Optional[str] = Field(default=None)
    email:          Optional[str] = Field(default=None)
    phone:          Optional[str] = Field(default=None)
    notes:          Optional[str] = Field(default=None)
    last_contacted: Optional[str] = Field(default=None)

class ContactDeleted(SQLModel):
    deleted: int

class InteractionBase(SQLModel):
    contact_id: int           = Field(description="Id of the contact")
    type:       str           = Field(description="Type of interaction: call, email, meeting, message, other")
    notes:      str           = Field(description="What was discussed or happened")
    date:       str           = Field(default_factory=lambda: date.today().isoformat(),
                                       description="ISO date string (YYYY-MM-DD), defaults to today")

class Interaction(InteractionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class InteractionCreate(InteractionBase):
    pass

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Personal CRM")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def create_tables():
    SQLModel.metadata.create_all(engine)

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/contacts/overdue", response_model=list[Contact], operation_id="list_overdue_contacts",
         summary="Lists contacts not reached out to in the last N days (default 30).")
def list_overdue_contacts(days: int = 30):
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    with Session(engine) as s:
        contacts = s.exec(select(Contact)).all()
        return [c for c in contacts
                if not c.last_contacted or c.last_contacted <= cutoff]

@app.get("/contacts", response_model=list[Contact], operation_id="list_contacts",
         summary="Lists all contacts.")
def list_contacts():
    with Session(engine) as s:
        return s.exec(select(Contact)).all()

@app.post("/contacts", response_model=Contact, status_code=201, operation_id="add_contact",
          summary="Adds a new contact.")
def add_contact(contact: ContactCreate):
    with Session(engine) as s:
        row = Contact.model_validate(contact)
        s.add(row); s.commit(); s.refresh(row)
        return row

@app.patch("/contacts/{contact_id}", response_model=Contact, operation_id="update_contact",
           summary="Updates a contact by id. Use this to update last_contacted after reaching out.")
def update_contact(contact_id: int, patch: ContactUpdate):
    with Session(engine) as s:
        row = s.get(Contact, contact_id)
        if not row:
            raise HTTPException(404, f"Contact {contact_id} not found")
        for k, v in patch.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        s.add(row); s.commit(); s.refresh(row)
        return row

@app.delete("/contacts/{contact_id}", response_model=ContactDeleted, operation_id="delete_contact",
            summary="Deletes a contact by id.")
def delete_contact(contact_id: int):
    with Session(engine) as s:
        row = s.get(Contact, contact_id)
        if not row:
            raise HTTPException(404, f"Contact {contact_id} not found")
        s.delete(row); s.commit()
        return ContactDeleted(deleted=contact_id)

@app.post("/contacts/{contact_id}/interactions", response_model=Interaction, status_code=201,
          operation_id="log_interaction",
          summary="Logs an interaction with a contact and updates their last_contacted date.")
def log_interaction(contact_id: int, interaction: InteractionCreate):
    with Session(engine) as s:
        contact = s.get(Contact, contact_id)
        if not contact:
            raise HTTPException(404, f"Contact {contact_id} not found")
        row = Interaction.model_validate({**interaction.model_dump(), "contact_id": contact_id})
        s.add(row)
        contact.last_contacted = interaction.date
        s.add(contact)
        s.commit(); s.refresh(row)
        return row

@app.get("/contacts/{contact_id}/interactions", response_model=list[Interaction],
         operation_id="list_interactions",
         summary="Lists all logged interactions for a contact, most recent first.")
def list_interactions(contact_id: int):
    with Session(engine) as s:
        rows = s.exec(select(Interaction).where(Interaction.contact_id == contact_id)).all()
        return sorted(rows, key=lambda x: x.date, reverse=True)

# ── Static ────────────────────────────────────────────────────────────────────

app.mount("/shared", StaticFiles(directory=str(SHARED)), name="shared")
app.mount("/", StaticFiles(directory="static", html=True), name="static")
