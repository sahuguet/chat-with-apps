# main.py
# FastAPI + SQLModel todo backend.
#
# Install:  pip install fastapi uvicorn sqlmodel httpx
# Run:      uvicorn main:app --reload
# API docs: http://localhost:8000/docs
# Schema:   http://localhost:8000/openapi.json

import os
from typing import Optional
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from sqlmodel import Field, Session, SQLModel, create_engine, select

# ── Database ──────────────────────────────────────────────────────────────────

DATABASE_URL = "sqlite:///./todos.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


# ── Models ────────────────────────────────────────────────────────────────────
# SQLModel unifies Pydantic (API validation + OpenAPI schema) and SQLAlchemy
# (DB table) in one class.  The same model drives:
#   • the SQLite table definition
#   • request/response validation
#   • the /openapi.json schema that the frontend consumes at runtime

class TodoBase(SQLModel):
    text: str  = Field(description="The todo text")
    done: bool = Field(default=False, description="Whether the todo is completed")

class Todo(TodoBase, table=True):
    """DB table + full response model (includes id)."""
    id: Optional[int] = Field(default=None, primary_key=True)

class TodoCreate(TodoBase):
    """Request body for POST /todos."""
    done: bool = Field(default=False, exclude=True)  # always False on create

class TodoUpdate(SQLModel):
    """Request body for PATCH /todos/{id}. All fields optional."""
    text: Optional[str]  = Field(default=None, description="New text")
    done: Optional[bool] = Field(default=None, description="Mark done/undone")

class TodoDeleted(SQLModel):
    """Response body for DELETE /todos/{id}."""
    deleted: int = Field(description="Id of the deleted todo")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Todo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def create_tables():
    SQLModel.metadata.create_all(engine)


# ── Routes ────────────────────────────────────────────────────────────────────
# operationId is the key the frontend uses as the function name in todoAPI,
# so we set them explicitly rather than relying on FastAPI's auto-generated ones.

@app.get(
    "/todos",
    response_model=list[Todo],
    operation_id="list_todos",
    summary="Returns all todos with their id, text, and done status.",
)
def list_todos():
    with Session(engine) as s:
        return s.exec(select(Todo)).all()


@app.post(
    "/todos",
    response_model=Todo,
    status_code=201,
    operation_id="add_todo",
    summary="Adds a new todo item.",
)
def add_todo(todo: TodoCreate):
    with Session(engine) as s:
        db_todo = Todo.model_validate(todo)
        s.add(db_todo)
        s.commit()
        s.refresh(db_todo)
        return db_todo


@app.patch(
    "/todos/{todo_id}",
    response_model=Todo,
    operation_id="update_todo",
    summary="Updates an existing todo by id. Can change text and/or done status.",
)
def update_todo(todo_id: int, patch: TodoUpdate):
    with Session(engine) as s:
        todo = s.get(Todo, todo_id)
        if not todo:
            raise HTTPException(status_code=404, detail=f"Todo {todo_id} not found")
        data = patch.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(todo, k, v)
        s.add(todo)
        s.commit()
        s.refresh(todo)
        return todo


@app.delete(
    "/todos/{todo_id}",
    response_model=TodoDeleted,
    operation_id="delete_todo",
    summary="Deletes a todo by id.",
)
def delete_todo(todo_id: int):
    with Session(engine) as s:
        todo = s.get(Todo, todo_id)
        if not todo:
            raise HTTPException(status_code=404, detail=f"Todo {todo_id} not found")
        s.delete(todo)
        s.commit()
        return TodoDeleted(deleted=todo_id)


@app.post(
    "/todos/clear-done",
    response_model=dict,
    operation_id="clear_done_todos",
    summary="Removes all completed todos.",
)
def clear_done_todos():
    with Session(engine) as s:
        done_todos = s.exec(select(Todo).where(Todo.done == True)).all()  # noqa: E712
        removed = len(done_todos)
        for todo in done_todos:
            s.delete(todo)
        s.commit()
        return {"removed": removed}


# ── Anthropic proxy ──────────────────────────────────────────────────────────
# Forwards chat requests to Anthropic server-side so the API key never
# reaches the browser and there are no CORS issues.
# Set the key via:  export ANTHROPIC_API_KEY=sk-ant-...

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

@app.post("/api/chat")
async def proxy_chat(payload: dict):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set on server")
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
        )
        return r.json()


# ── Serve the frontend ────────────────────────────────────────────────────────
# Place index.html in a ./static/ folder next to main.py.
# The frontend is then available at http://localhost:8000/

app.mount("/", StaticFiles(directory="static", html=True), name="static")
