from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
import json
import os
import requests
import datetime
import re
from openai import OpenAI
from playwright.async_api import async_playwright


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
{task}

do the task given and only give one word no instruction nothing just one word
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


async def payme(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(url, wait_until="networkidle")
        pre_text = await page.inner_text("pre")

        print("Rendered PRE text:")
        print(pre_text)

        await browser.close()

    return pre_text



async def solve_quiz(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")

        # 1) Extract the quiz text (example: “Sum the value column on page 2…”)
        quiz_text = await page.inner_text("#question")  # depends on site

        # 2) You must parse the instructions and solve
        answer = ask_chatgpt(quiz_text)

        # 3) Find where to POST the answer (hidden in HTML form)
        submit_url = await page.get_attribute("form", "action")

        await browser.close()
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
        quiz = await solve_quiz(data["url"])
        payl = await payme(data["url"])



    except Exception as e:
        raise HTTPException(status_code=500, detail = f"Failed to fetch URL: {str(e)}")

    return JSONResponse(
        status_code=200,
        content={"status": "ok", "payload": payl, "content": quiz, "chatgpt": "answer_json"}
    )

