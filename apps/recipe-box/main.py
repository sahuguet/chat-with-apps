# apps/recipe-box/main.py
# Run: uvicorn main:app --reload --port 8002

from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Field, Session, SQLModel, create_engine, select

# ── Database ──────────────────────────────────────────────────────────────────

engine = create_engine("sqlite:///./recipes.db", connect_args={"check_same_thread": False})

SHARED = Path(__file__).resolve().parent.parent.parent / "static"

# ── Models ────────────────────────────────────────────────────────────────────

class RecipeBase(SQLModel):
    name:         str           = Field(description="Recipe name")
    ingredients:  str           = Field(description="Comma-separated list of ingredients")
    instructions: str           = Field(description="Step-by-step cooking instructions")
    servings:     int           = Field(default=2, description="Number of servings")
    tags:         str           = Field(default="", description="Comma-separated tags e.g. vegetarian, quick, italian")

class Recipe(RecipeBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class RecipeCreate(RecipeBase):
    pass

class RecipeUpdate(SQLModel):
    name:         Optional[str] = Field(default=None)
    ingredients:  Optional[str] = Field(default=None)
    instructions: Optional[str] = Field(default=None)
    servings:     Optional[int] = Field(default=None)
    tags:         Optional[str] = Field(default=None)

class RecipeDeleted(SQLModel):
    deleted: int

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Recipe Box")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def create_tables():
    SQLModel.metadata.create_all(engine)

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/recipes/search", response_model=list[Recipe], operation_id="search_recipes",
         summary="Searches recipes by ingredient or tag. Returns all recipes if query is empty.")
def search_recipes(q: str = ""):
    with Session(engine) as s:
        recipes = s.exec(select(Recipe)).all()
        if not q:
            return recipes
        ql = q.lower()
        return [r for r in recipes
                if ql in r.ingredients.lower() or ql in r.tags.lower() or ql in r.name.lower()]

@app.get("/recipes", response_model=list[Recipe], operation_id="list_recipes",
         summary="Lists all recipes with their ingredients, instructions, and tags.")
def list_recipes():
    with Session(engine) as s:
        return s.exec(select(Recipe)).all()

@app.get("/recipes/{recipe_id}", response_model=Recipe, operation_id="get_recipe",
         summary="Returns a single recipe by id, including full instructions.")
def get_recipe(recipe_id: int):
    with Session(engine) as s:
        row = s.get(Recipe, recipe_id)
        if not row:
            raise HTTPException(404, f"Recipe {recipe_id} not found")
        return row

@app.post("/recipes", response_model=Recipe, status_code=201, operation_id="add_recipe",
          summary="Adds a new recipe to the collection.")
def add_recipe(recipe: RecipeCreate):
    with Session(engine) as s:
        row = Recipe.model_validate(recipe)
        s.add(row); s.commit(); s.refresh(row)
        return row

@app.patch("/recipes/{recipe_id}", response_model=Recipe, operation_id="update_recipe",
           summary="Updates an existing recipe by id.")
def update_recipe(recipe_id: int, patch: RecipeUpdate):
    with Session(engine) as s:
        row = s.get(Recipe, recipe_id)
        if not row:
            raise HTTPException(404, f"Recipe {recipe_id} not found")
        for k, v in patch.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        s.add(row); s.commit(); s.refresh(row)
        return row

@app.delete("/recipes/{recipe_id}", response_model=RecipeDeleted, operation_id="delete_recipe",
            summary="Deletes a recipe by id.")
def delete_recipe(recipe_id: int):
    with Session(engine) as s:
        row = s.get(Recipe, recipe_id)
        if not row:
            raise HTTPException(404, f"Recipe {recipe_id} not found")
        s.delete(row); s.commit()
        return RecipeDeleted(deleted=recipe_id)

# ── Static ────────────────────────────────────────────────────────────────────

app.mount("/shared", StaticFiles(directory=str(SHARED)), name="shared")
app.mount("/", StaticFiles(directory="static", html=True), name="static")
