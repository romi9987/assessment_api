from fastapi import FastAPI

from database import Base, engine
from routers import patients

app = FastAPI()
app.include_router(patients.router)

Base.metadata.create_all(bind=engine)

@app.get("/")
def main():
    return {
        "app_name": "Assessment API",
        "version": 1,
        "description": "Assess and keep patient data.",
        "status": "active"
    }
        