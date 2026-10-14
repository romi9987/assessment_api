"""Check the column names in patients database."""

from sqlalchemy import inspect

from database import engine

inspector = inspect(engine)

columns = inspector.get_columns("patients")

for column in columns:
    print(column["name"], column["type"], column["nullable"])