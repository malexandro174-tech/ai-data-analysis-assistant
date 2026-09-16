from fastapi import APIRouter

router = APIRouter()


def make_health(app):
    @router.get("/health")
    async def health():
        return {"status": "healthy", "service": "ai-data-analyst-workspace", "broker_ready": app.state.services.broker_ready, "metrics": app.state.workspace.metrics().model_dump()}
    return router
