from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
import json
import os
import requests
import datetime
import re
from openai import OpenAI
import asyncio
import httpx
from bs4 import BeautifulSoup


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
        "input": f"""
You are an automated agent. Read the content below Use this origin:

CONTENT:
what is the sum of 1234+123

do the task given and only give one word no instruction nothing just one word 0 if no answer
"""
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


async def payme(url: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "html.parser")
    pre_tag = soup.find("pre")
    pre_text = pre_tag.get_text(strip=True) if pre_tag else ""
    try:
        data = json.loads(pre_text)
    except json.JSONDecodeError:
        raise ValueError("The <pre> content is not valid JSON")

    return data


async def solve_quiz(url: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "html.parser")

    # 1) Extract the quiz text
    question_tag = soup.select_one("#question")
    quiz_text = question_tag.get_text(strip=True) if question_tag else ""

    # 2) Solve the quiz (replace with your AI function)
    answer = ask_chatgpt(quiz_text)  # your own function

    # 3) Get the form action (submit URL)
    form_tag = soup.find("form")
    submit_url = form_tag.get("action") if form_tag else url

    return answer, submit_url


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
        k = data["url"]
        quiz = await solve_quiz(data["url"])
        parts = k.rstrip("/").split("/")
        parts[-1] = "submit"
        submit_url = "/".join(parts)
        a = await payme(data["url"])
        a['email'] = "hrithivk"
        a['answer'] = str(quiz[0]["output"][0]["content"][0]["text"])
        a['url'] = k
        async with httpx.AsyncClient() as client:
            response = await client.post(submit_url, json=a)
                
        response.raise_for_status()


    except Exception as e:
        raise HTTPException(status_code=500, detail = f"Failed to fetch URL: {str(e)}")

    return JSONResponse(
        status_code=200,
        content={"status": "ok", "payload": submit_url, "content": a, "response":response.json()}
    )

