from fastapi import FastAPI
from app.api.routers.health import router as health_router
from app.api.routers.bot import router as bot_router

app = FastAPI(title="ForexAI Backend", version="0.1.0")
app.include_router(health_router, prefix="/api")
app.include_router(bot_router, prefix="/api")


@app.get("/")
def root():
    return {"message": "ForexAI backend is running"}
