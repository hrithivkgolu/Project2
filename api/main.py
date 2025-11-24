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


GOOGLE_FORM_SECRET = "HrithProj2"

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
    try:
        response = requests.get(data["url"], timeout=10)
        fetched_text = response.text
        fetched_status = response.status_code

    except Exception as e:
        raise HTTPException(status_code=500, detail = f"Failed to fetch URL: {str(e)}")


    return JSONResponse(
        status_code=200,
        content={"status": "ok", "url_status": fetched_status, "content": fetched_text}
    )
