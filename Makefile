# Minimal Makefile com aliases para docker-compose (dev / dev-build / health)

COMPOSE := docker-compose
DEV_FLAGS := -f docker-compose.yml -f docker-compose.dev.yml
PROD_FLAGS := -f docker-compose.yml -f docker-compose.prod.yml

.PHONY: phony help up up-detach build down logs ps health \
        dev-build dev-down dev-logs dev-ps dev-health \
        prod-build prod-up prod-up-detach prod-down prod-logs prod-ps prod-health

phony: help

help:
	@echo "Makefile - aliases úteis"
	@echo ""
	@echo "Dev (default):"
	@echo "  make up           -> docker-compose (dev) up --build"
	@echo "  make up-detach    -> docker-compose (dev) up --build -d"
	@echo "  make dev-build    -> docker-compose (dev) build --no-cache"
	@echo "  make dev-down     -> docker-compose (dev) down --remove-orphans"
	@echo "  make dev-logs     -> docker-compose (dev) logs -f"
	@echo "  make dev-ps       -> docker-compose (dev) ps"
	@echo "  make dev-health   -> checa http://localhost:5000"
	@echo ""
	@echo "Prod:"
	@echo "  make prod-build       -> docker-compose (prod) build --no-cache"
	@echo "  make prod-up          -> docker-compose (prod) up --build -d"
	@echo "  make prod-up-detach   -> alias for prod-up"
	@echo "  make prod-down        -> docker-compose (prod) down"
	@echo "  make prod-logs        -> docker-compose (prod) logs -f"
	@echo "  make prod-ps          -> docker-compose (prod) ps"
	@echo "  make prod-health      -> checa http://localhost:8000"
	@echo ""
	@echo "Misc:"
	@echo "  make build    -> alias for prod-build"
	@echo "  make down     -> alias for dev-down"
	@echo "  make logs     -> alias for dev-logs"
	@echo "  make ps       -> alias for dev-ps"
	@echo "  make health   -> alias for dev-health"

# --- Dev (default) ---
up:
	@echo ">>> docker-compose $(DEV_FLAGS) up --build"
	$(COMPOSE) $(DEV_FLAGS) up --build

up-detach:
	@echo ">>> docker-compose $(DEV_FLAGS) up --build -d"
	$(COMPOSE) $(DEV_FLAGS) up --build -d

dev-build:
	@echo ">>> docker-compose $(DEV_FLAGS) build --no-cache"
	$(COMPOSE) $(DEV_FLAGS) build --no-cache

dev-down:
	@echo ">>> docker-compose $(DEV_FLAGS) down --remove-orphans"
	$(COMPOSE) $(DEV_FLAGS) down --remove-orphans

dev-logs:
	@echo ">>> docker-compose $(DEV_FLAGS) logs -f"
	$(COMPOSE) $(DEV_FLAGS) logs -f

dev-ps:
	@echo ">>> docker-compose $(DEV_FLAGS) ps"
	$(COMPOSE) $(DEV_FLAGS) ps

dev-health:
	@echo "Checking backend health at http://localhost:5000 ..."
	@sh -c 'i=0; until [ $$i -ge 15 ]; do if curl -sSf http://localhost:5000 >/dev/null 2>&1; then echo "backend OK"; exit 0; fi; i=$$((i+1)); sleep 1; done; echo "backend UNHEALTHY"; exit 1'

# convenience aliases to match original names
build: prod-build
down: dev-down
logs: dev-logs
ps: dev-ps
health: dev-health

# --- Prod ---
prod-build:
	@echo ">>> docker-compose $(PROD_FLAGS) build --no-cache"
	$(COMPOSE) $(PROD_FLAGS) build --no-cache

prod-up:
	@echo ">>> docker-compose $(PROD_FLAGS) up --build -d"
	$(COMPOSE) $(PROD_FLAGS) up --build -d

prod-up-detach: prod-up

prod-down:
	@echo ">>> docker-compose $(PROD_FLAGS) down"
	$(COMPOSE) $(PROD_FLAGS) down

prod-logs:
	@echo ">>> docker-compose $(PROD_FLAGS) logs -f"
	$(COMPOSE) $(PROD_FLAGS) logs -f

prod-ps:
	@echo ">>> docker-compose $(PROD_FLAGS) ps"
	$(COMPOSE) $(PROD_FLAGS) ps

prod-health:
	@echo "Checking backend health at http://localhost:8000 ..."
	@sh -c 'i=0; until [ $$i -ge 15 ]; do if curl -sSf http://localhost:8000 >/dev/null 2>&1; then echo "backend OK"; exit 0; fi; i=$$((i+1)); sleep 1; done; echo "backend UNHEALTHY"; exit 1'