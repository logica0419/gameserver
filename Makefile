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
	tbls doc
