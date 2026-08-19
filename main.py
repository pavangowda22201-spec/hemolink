"""
RUN LOCATION: Run this file from the project root (the "hemolink" folder) to start the API server.
    cd hemolink
    uvicorn main:app --reload

Once running, open http://localhost:8000/docs for interactive API docs.
"""
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import donors, requests, acceptances

# Creates tables if they don't exist yet (fine for dev; use Alembic migrations in production).
Base.metadata.create_all(bind=engine)

app = FastAPI(title="HemoLink — Blood Donor Matching API")

app.include_router(donors.router)
app.include_router(requests.router)
app.include_router(acceptances.router)

# Serves the web app at http://localhost:8000/app
# (the API itself still lives at /donors, /requests, /acceptances, /docs)
app.mount("/app", StaticFiles(directory="static", html=True), name="static")


@app.get("/")
def root():
    return FileResponse("static/index.html")