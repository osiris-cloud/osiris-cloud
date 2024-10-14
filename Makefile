ifeq ($(OS),Windows_NT)
$(error Use ".\make" instead of make on Windows)
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

django: venv
	@echo "### Starting Django"
	./venv/bin/python3 manage.py runserver

web: node_modules
	@echo "### Starting Flowbite"
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
	npx tailwindcss -i ./static/assets/style.css -o ./static/dist/css/output.css
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

.PHONY: clean
clean:
	@echo "### Deleting virtual environment"
	rm -rf $$(find -name __pycache__) venv node_modules package-lock.json staticfiles/*

.PHONY: delete
delete:
	@echo "### Deleting DB"
	rm -f db.sqlite3
	cp db-orig.sqlite3 db.sqlite3

.INTERRUPT:
	@exit 1
