from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
import json
import os
from github import Github
import requests
import datetime
import re
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


app = FastAPI(title="QUIZ")




@app.get("/")
async def root():
    return {
        "service": "I am here",
        "status": "OK",
        "endpoint": "/receive (POST)"
    }


GOOGLE_FORM_SECRET = "your secret"

@app.post("/receive")
async def receive(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    if "secret" not in data:
        raise HTTPException(status_code=400, detail="Missing 'secret' field")
    if data["secret"] != GOOGLE_FORM_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden: secret mismatch")
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "message": "Secret verified"}
    )
