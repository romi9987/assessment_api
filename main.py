from fastapi import FastAPI

# from database import Base, engine
from routers import assessments, patients

app = FastAPI()
app.include_router(patients.router)
app.include_router(assessments.router)

# Once you've verified the baseline with alembic, you can remove this line from main.py
# An important consequence: when setting up your project with a new, empty database, you'll need to run alembic upgrade head before using the API.
# Base.metadata.create_all(bind=engine)

@app.get("/")
def main():
    return {
        "app_name": "Assessment API",
        "version": 1,
        "description": "Assess and keep patient data.",
        "status": "active"
    }
        