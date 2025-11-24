from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
import json
import os
import requests
import datetime
import re
from openai import OpenAI


app = FastAPI(title="QUIZ")

GOOGLE_FORM_SECRET = "HrithProj2"

AI_PIPE_TOKEN = os.getenv("OPENAI_API_KEY")


def ask_chatgpt(task):
    url = "https://aipipe.org/openrouter/v1/responses"
    headers = {
        "Authorization": f"Bearer {AI_PIPE_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openai/gpt-4.1-nano",
        "input": task
    }
    r = requests.post(url, json=payload, headers=headers)
    return r.json()



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
        answer_json = ask_chatgpt(fetched_text)

    except Exception as e:
        raise HTTPException(status_code=500, detail = f"Failed to fetch URL: {str(e)}")

    return JSONResponse(
        status_code=200,
        content={"status": "ok", "url_status": fetched_status, "content": fetched_text, "chatgpt": answer_json}
    )

