.PHONY: help run stop todo expense-tracker recipe-box personal-crm pantry-manager

# ── Ports ─────────────────────────────────────────────────────────────────────
PORT_TODO    = 8000
PORT_EXPENSE = 8001
PORT_RECIPE  = 8002
PORT_CRM     = 8003
PORT_PANTRY  = 8004

help:
	@echo ""
	@echo "  chat-with-apps"
	@echo ""
	@echo "  make run              Start all 4 demo apps (Ctrl+C stops all)"
	@echo "  make stop             Stop all running apps"
	@echo ""
	@echo "  make todo             Todo reference app     http://localhost:$(PORT_TODO)"
	@echo "  make expense-tracker  Expense tracker        http://localhost:$(PORT_EXPENSE)"
	@echo "  make recipe-box       Recipe box             http://localhost:$(PORT_RECIPE)"
	@echo "  make personal-crm     Personal CRM           http://localhost:$(PORT_CRM)"
	@echo "  make pantry-manager   Pantry manager         http://localhost:$(PORT_PANTRY)"
	@echo ""

# ── Individual apps ───────────────────────────────────────────────────────────

todo:
	uvicorn main:app --reload --port $(PORT_TODO)

expense-tracker:
	cd apps/expense-tracker && uvicorn main:app --reload --port $(PORT_EXPENSE)

recipe-box:
	cd apps/recipe-box && uvicorn main:app --reload --port $(PORT_RECIPE)

personal-crm:
	cd apps/personal-crm && uvicorn main:app --reload --port $(PORT_CRM)

pantry-manager:
	cd apps/pantry-manager && uvicorn main:app --reload --port $(PORT_PANTRY)

# ── Run all apps concurrently ─────────────────────────────────────────────────
# Ctrl+C kills the whole process group cleanly.
# Each app's output is prefixed with its name for easy reading.

run:
	@echo "Starting all apps — Ctrl+C to stop all"
	@echo ""
	@echo "  Expense Tracker  →  http://localhost:$(PORT_EXPENSE)"
	@echo "  Recipe Box       →  http://localhost:$(PORT_RECIPE)"
	@echo "  Personal CRM     →  http://localhost:$(PORT_CRM)"
	@echo "  Pantry Manager   →  http://localhost:$(PORT_PANTRY)"
	@echo ""
	@trap 'kill 0' INT; \
	(cd apps/expense-tracker && uvicorn main:app --port $(PORT_EXPENSE) 2>&1 | sed 's/^/[expense] /') & \
	(cd apps/recipe-box      && uvicorn main:app --port $(PORT_RECIPE)  2>&1 | sed 's/^/[recipe ] /') & \
	(cd apps/personal-crm    && uvicorn main:app --port $(PORT_CRM)     2>&1 | sed 's/^/[crm    ] /') & \
	(cd apps/pantry-manager  && uvicorn main:app --port $(PORT_PANTRY)  2>&1 | sed 's/^/[pantry ] /') & \
	wait

# ── Stop ──────────────────────────────────────────────────────────────────────

stop:
	@pkill -f "uvicorn main:app" && echo "All apps stopped." || echo "No apps running."
