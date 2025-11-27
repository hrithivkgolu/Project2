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

GOOGLE_FORM_SECRET = os.getenv("FORM_KEY")

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



async def payme(url: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    pre = soup.find("pre")
    if not pre:
        div = soup.find("div")
        if div:
            pre = div.find("pre")

    if not pre:
        return None

    raw = pre.get_text().strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


async def solve_quiz(url: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "html.parser")

    question_tag = soup.select_one("#question")
    quiz_text = question_tag.get_text(strip=True) if question_tag else ""

    answer = ask_chatgpt(quiz_text)  

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
        count = 1
        current_url = data["url"]
        collected = [] 
        postedto = []

        while current_url:
            if count <=1:
                a = await payme(current_url)
                count += 1
            parts = current_url.rstrip("/").split("/")
            parts[-1] = "submit"
            submit_url = "/".join(parts)
            quiz = await solve_quiz(current_url)
            g = quiz[0]["output"][0]["content"][0]["text"]
            a['email'] = data['email']
            a['secret'] = data['secret']
            a['answer'] = g
            a['url'] = current_url
            postedto.append(a)
            async with httpx.AsyncClient() as client:
                response = await client.post(submit_url, json=a)
                response.raise_for_status()

            response_json = response.json()
            collected.append(response_json)
            current_url = response_json.get("url")

            if not current_url:
                break

        return JSONResponse(
            status_code=200,
            content={
                "status": "done",
                "chain": collected  
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed: {str(e)}") 

    
