#!/usr/bin/env python3
"""Seed all demo apps with sample data."""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent


def seed(db_path: Path, table: str, columns: list[str], rows: list[tuple], create_sql: str):
    """Create table if needed, insert rows only if table is empty."""
    conn = sqlite3.connect(db_path)
    conn.execute(create_sql)
    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    if count == 0:
        placeholders = ", ".join("?" * len(columns))
        conn.executemany(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})", rows)
        print(f"  {db_path.parent.name}: inserted {len(rows)} rows into {table}")
    else:
        print(f"  {db_path.parent.name}: {table} already has data, skipping")
    conn.commit()
    conn.close()


# ── Expense Tracker ───────────────────────────────────────────────────────────

seed(
    db_path=ROOT / "apps/expense-tracker/expenses.db",
    table="expense",
    create_sql="""CREATE TABLE IF NOT EXISTS expense (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT    NOT NULL,
        amount      REAL    NOT NULL,
        category    TEXT    NOT NULL,
        date        TEXT    NOT NULL
    )""",
    columns=["description", "amount", "category", "date"],
    rows=[
        ("Whole Foods grocery run",    87.43,  "food",          "2026-06-10"),
        ("Uber to airport",            24.50,  "transport",     "2026-06-09"),
        ("Monthly electricity bill",   94.20,  "utilities",     "2026-06-01"),
        ("Netflix subscription",       15.99,  "entertainment", "2026-06-01"),
        ("Lunch at Shake Shack",        22.75,  "food",          "2026-06-12"),
    ],
)

# ── Recipe Box ────────────────────────────────────────────────────────────────

seed(
    db_path=ROOT / "apps/recipe-box/recipes.db",
    table="recipe",
    create_sql="""CREATE TABLE IF NOT EXISTS recipe (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        name         TEXT    NOT NULL,
        ingredients  TEXT    NOT NULL,
        instructions TEXT    NOT NULL,
        servings     INTEGER NOT NULL,
        tags         TEXT    NOT NULL DEFAULT ''
    )""",
    columns=["name", "ingredients", "instructions", "servings", "tags"],
    rows=[
        (
            "Pasta Carbonara",
            "spaghetti, eggs, pancetta, parmesan, black pepper, salt",
            "1. Cook spaghetti al dente. 2. Fry pancetta until crispy. "
            "3. Whisk eggs with parmesan. 4. Toss hot pasta with pancetta, "
            "remove from heat, add egg mixture, toss quickly. Season with pepper.",
            2, "italian, quick, pasta",
        ),
        (
            "Chicken Stir Fry",
            "chicken breast, broccoli, soy sauce, ginger, garlic, sesame oil, rice",
            "1. Cook rice. 2. Slice chicken, marinate in soy sauce and ginger. "
            "3. Stir fry garlic in sesame oil, add chicken, then broccoli. "
            "4. Toss with remaining soy sauce. Serve over rice.",
            3, "asian, quick, chicken",
        ),
        (
            "Banana Oat Pancakes",
            "ripe bananas, eggs, rolled oats, cinnamon, maple syrup, butter",
            "1. Mash bananas. 2. Blend with eggs and oats into a batter. "
            "3. Add cinnamon. 4. Cook on buttered pan over medium heat, "
            "2-3 min per side. Serve with maple syrup.",
            2, "breakfast, vegetarian, quick",
        ),
        (
            "Roasted Lemon Salmon",
            "salmon fillet, lemon, olive oil, garlic, fresh dill, salt, pepper",
            "1. Preheat oven to 200°C. 2. Place salmon on baking sheet, "
            "drizzle with olive oil, season. 3. Top with lemon slices, garlic, dill. "
            "4. Roast 12-15 min until flaky.",
            2, "fish, healthy, oven",
        ),
        (
            "Red Lentil Soup",
            "red lentils, onion, garlic, canned tomatoes, cumin, coriander, vegetable stock, olive oil",
            "1. Sauté diced onion and garlic in olive oil. 2. Add spices, toast 1 min. "
            "3. Add rinsed lentils, tomatoes, and stock. 4. Simmer 25 min until lentils dissolve. "
            "Season to taste.",
            4, "vegetarian, soup, healthy",
        ),
    ],
)

# ── Personal CRM ──────────────────────────────────────────────────────────────

seed(
    db_path=ROOT / "apps/personal-crm/crm.db",
    table="contact",
    create_sql="""CREATE TABLE IF NOT EXISTS contact (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        name           TEXT NOT NULL,
        email          TEXT,
        phone          TEXT,
        notes          TEXT,
        last_contacted TEXT
    )""",
    columns=["name", "email", "phone", "notes", "last_contacted"],
    rows=[
        ("Sarah Chen",      "sarah.chen@example.com",   "+1-415-555-0101",
         "Met at PyCon 2025. Works on ML infra at Stripe.", "2026-06-08"),
        ("Marcus Williams", "marcus.w@example.com",     "+1-212-555-0134",
         "Former colleague, now at Anthropic. Great for AI discussions.", "2026-05-01"),
        ("Priya Patel",     "priya.patel@example.com",  None,
         "Investor at a16z. Interested in developer tools.", "2026-06-02"),
        ("James O'Brien",   "james.obrien@example.com", "+1-628-555-0177",
         "Potential advisor. Hasn't replied to last two emails.", "2026-04-10"),
        ("Yuki Tanaka",     "yuki@example.com",         "+1-650-555-0198",
         "Product designer, collaborating on the Chrome extension idea.", "2026-06-11"),
    ],
)

seed(
    db_path=ROOT / "apps/personal-crm/crm.db",
    table="interaction",
    create_sql="""CREATE TABLE IF NOT EXISTS interaction (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        contact_id INTEGER NOT NULL,
        type       TEXT    NOT NULL,
        notes      TEXT    NOT NULL,
        date       TEXT    NOT NULL
    )""",
    columns=["contact_id", "type", "notes", "date"],
    rows=[
        (1, "meeting", "Coffee catchup. She's hiring a senior engineer, asked if I know anyone.", "2026-06-08"),
        (2, "email",   "Sent intro to the chat-with-apps repo. He offered to give feedback.",     "2026-05-01"),
        (3, "call",    "30-min intro call. She wants to see a demo before next board meeting.",    "2026-06-02"),
        (5, "meeting", "Working session on UX for the extension popup UI. Very productive.",       "2026-06-11"),
        (1, "email",   "Forwarded job spec for her open role.",                                   "2026-05-20"),
    ],
)

# ── Pantry Manager ────────────────────────────────────────────────────────────

seed(
    db_path=ROOT / "apps/pantry-manager/pantry.db",
    table="pantryitem",
    create_sql="""CREATE TABLE IF NOT EXISTS pantryitem (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        name         TEXT NOT NULL,
        quantity     REAL NOT NULL,
        unit         TEXT NOT NULL,
        category     TEXT NOT NULL,
        min_quantity REAL NOT NULL DEFAULT 1.0
    )""",
    columns=["name", "quantity", "unit", "category", "min_quantity"],
    rows=[
        ("Olive oil",      0.3,  "liters", "pantry",    1.0),   # LOW
        ("Pasta",          1.5,  "kg",     "pantry",    0.5),
        ("Eggs",           3.0,  "count",  "dairy",     6.0),   # LOW
        ("Chicken breast", 1.2,  "kg",     "frozen",    0.5),
        ("Coffee beans",   0.08, "kg",     "beverages", 0.25),  # LOW
    ],
)

print("\nDone.")
