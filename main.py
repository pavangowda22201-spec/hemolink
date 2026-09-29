from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import (
    Base,
    engine,
    ensure_donor_user_id_column,
    ensure_blood_request_schema,
    ensure_acceptance_user_id_column,
)
from app.routers import donors, requests, acceptances, auth


Base.metadata.create_all(bind=engine)

ensure_donor_user_id_column()
ensure_blood_request_schema()
ensure_acceptance_user_id_column()


app = FastAPI(title="HemoLink - Blood Donor Matching API")


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://10.57.13.88:5173",
        "http://localhost:5174",
        "https://hemo-link-dashboard.vercel.app",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# API ROUTERS
# ---------------------------------------------------------

app.include_router(donors.router)
app.include_router(requests.router)
app.include_router(acceptances.router)
app.include_router(auth.router)


# ---------------------------------------------------------
# HEMOLINK WEB APP
# ---------------------------------------------------------

app.mount(
    "/app",
    StaticFiles(directory="static", html=True),
    name="static",
)


@app.get("/")
def root():
    return FileResponse("static/index.html")
