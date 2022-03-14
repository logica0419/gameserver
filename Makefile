run:
	uvicorn app.api:app --reload

format:
	isort app tests
	black app tests

test:
	pytest -sv tests/*

recreate:
	mysql webapp < schema.sql

tbls:
	rm -r ./docs/db_schema
	tbls doc
