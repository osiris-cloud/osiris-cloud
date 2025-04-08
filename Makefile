ifeq ($(OS),Windows_NT)
$(error Use local make ".\make" instead of Windows Make)
endif

PYTHON := python3.12

help:
	@echo '### Available make targets:'
	@grep PHONY: Makefile | cut -d: -f2 | sed '1d;s/^/make/'

venv:
	@if [ ! -d venv ]; then \
  		echo "### Creating virtual environment"; \
		$(PYTHON) -m venv venv; \
		./venv/bin/python3 -m pip install --upgrade pip; \
		./venv/bin/pip install -r requirements.txt; \
	fi

node_modules:
	npm install

.PHONY: django
django: venv
	@echo "### Starting Django"
	./venv/bin/python3 manage.py runserver

.PHONY: django-https
django-https: venv
	@echo "### Starting Django with HTTPS"
	./venv/bin/python3 -m daphne -e ssl:8000:privateKey=./dev-certs/localhost.key:certKey=./dev-certs/localhost.crt --proxy-headers core.asgi:application

.PHONY: web
web: node_modules
	@echo "### Starting Webpack"
	npm run dev

celery:
	@echo "### Starting Celery"
	./venv/bin/python3 -m celery -A core worker --loglevel INFO

.PHONY: dev
dev: venv node_modules
	@echo "### starting app and DB"
	$(MAKE) -j3 django celery web

.PHONY: build
build: node_modules
	@echo "### Building app"
	npm run build
	./venv/bin/python3 python manage.py collectstatic --no-input

.PHONY: migrations
migrations: venv
	@echo "### Making migrations"
	./venv/bin/python3 manage.py makemigrations
	./venv/bin/python3 manage.py migrate

.PHONY: app
app: venv
	@echo "### Creating app"
	APP_NAME=$(filter-out $@, $(MAKECMDGOALS));
	mkdir apps/$APP_NAME; ./venv/bin/python3 manage.py startapp $APP_NAME apps/$APP_NAME
%:
	@true

.PHONY: index
algolia-reindex: venv
	@echo "### Reindexing Algolia"
	./venv/bin/python3 manage.py algolia_reindex

.PHONY: clear-index
algolia-clear: venv
	@echo "### Clearing Algolia index"
	./venv/bin/python3 manage.py algolia_clear

.PHONY: clean
clean:
	@echo "### Deleting virtual environment"
	rm -rf $$(find -name __pycache__) venv node_modules package-lock.json staticfiles/*

.PHONY: reset
delete:
	@echo "### Deleting DB"
	rm -f db.sqlite3
	cp db-orig.sqlite3 db.sqlite3
	@echo "### DB reset"

.INTERRUPT:
	@exit 1
