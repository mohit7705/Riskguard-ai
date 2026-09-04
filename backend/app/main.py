from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routes.risk import router as risk_router
from backend.app.routes.report import router as report_router
from backend.app.routes.assignment import router as assignment_router

app = FastAPI(
    title="RiskGuard AI",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://riskguard-ai-one.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(risk_router)
app.include_router(report_router)
app.include_router(assignment_router)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "riskguard-ai",
    }
