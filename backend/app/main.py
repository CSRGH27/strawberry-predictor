from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from . import models
from .routes import router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Strawberry Predictor API",
    description="API de prédiction de production de fraises",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En prod, mettre les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
def root():
    return {
        "message": "Bienvenue sur l'API Strawberry Predictor",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}