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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


def ask_chatgpt(task_content: str):
    prompt = f"""
You are an automated agent. Read the content below and figure out what JSON
needs to be submitted. Use this origin:.

CONTENT:
{task_content}

Return ONLY the JSON body to POST. No explanation.
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt
    )

    return response.output_text



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

