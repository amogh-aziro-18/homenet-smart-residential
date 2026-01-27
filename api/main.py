from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import tasks, assets, reports
from services.task_service import TaskService

from db.session import init_db
from services.notification_service import NotificationService
from api.routes import alerts


app = FastAPI(title="HOMENET Water POC")

# ✅ Create SINGLE global TaskService
app.state.notification_service = NotificationService()

app.include_router(alerts.router, tags=["alerts"])


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "service": "homenet-water-poc"}

@app.on_event("startup")
def startup():
    init_db()


app.include_router(tasks.router, tags=["tasks"])
app.include_router(assets.router, tags=["assets"])
app.include_router(reports.router, tags=["reports"])
