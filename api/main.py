from fastapi import FastAPI

app = FastAPI(title="HOMENET POC API")

@app.get("/health")
def health_check():
    return {"status": "ok"}
