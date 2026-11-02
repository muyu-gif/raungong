from fastapi import FastAPI

app = FastAPI(title="活动智囊 API")


@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "activity-mind"}

feat(backend): add FastAPI skeleton
