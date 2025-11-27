from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import json, os, requests, httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from openai import OpenAI
import asyncio

app = FastAPI(title="QUIZ")

GOOGLE_FORM_SECRET = os.getenv("FORM_KEY")
AI_PIPE_TOKEN = os.getenv("OPENAI_API_KEY")


# ------------------------------------------------------------
#  Ask GPT
# ------------------------------------------------------------
def ask_chatgpt(task: str):
    url = "https://aipipe.org/openrouter/v1/responses"
    headers = {
        "Authorization": f"Bearer {AI_PIPE_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openai/gpt-4.1-nano",
        "input": f"Give ONE WORD answer for:\n{task}\nIf no answer say 0."
    }
    r = requests.post(url, json=payload, headers=headers)
    return r.json()


# ------------------------------------------------------------
# EXTRACT JSON FROM FIRST PAGE
# ------------------------------------------------------------
async def payme(url: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    pre = soup.find("pre")

    if not pre:
        raise Exception("No <pre> JSON found on page")

    try:
        raw = pre.get_text().strip()
        return json.loads(raw)
    except:
        raise Exception("Invalid JSON inside <pre>")


# ------------------------------------------------------------
# SOLVE A QUIZ PAGE
# ------------------------------------------------------------
async def solve_quiz(url: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "html.parser")

    # Detect type
    def detect_quiz_type():
        if soup.select_one("table"): return "scrape"
        if soup.select_one("audio"): return "audio"
        if soup.select_one(".n1") or soup.select_one(".n2"): return "math"
        return "text"

    quiz_type = detect_quiz_type()

    # SCRAPE TYPE
    if quiz_type == "scrape":
        table = soup.select_one("table")
        rows = table.find_all("tr")
        extracted = [
            " | ".join([td.get_text(strip=True) for td in tr.find_all(["td", "th"])])
            for tr in rows
        ]
        task_text = "\n".join(extracted)
        answer = ask_chatgpt(task_text)

    # AUDIO TYPE
    elif quiz_type == "audio":
        audio_tag = soup.select_one("audio")
        audio_url = urljoin(url, audio_tag.get("src"))

        async with httpx.AsyncClient() as client:
            audio_file = await client.get(audio_url)
            audio_file.raise_for_status()
            audio_bytes = audio_file.content

        ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        result = ai.audio.transcriptions.create(
            file=("audio.wav", audio_bytes),
            model="gpt-4o-mini-tts"
        )
        transcript = result.text.strip()
        answer = ask_chatgpt(transcript)

    # MATH TYPE
    elif quiz_type == "math":
        a = int(soup.select_one(".n1").get_text(strip=True))
        b = int(soup.select_one(".n2").get_text(strip=True))
        return str(a + b), url

    # TEXT TYPE
    else:
        q = soup.select_one("#q") or soup.select_one("#question")
        quiz_text = q.get_text(strip=True) if q else ""
        answer = ask_chatgpt(quiz_text)

    # Extract next URL
    form_tag = soup.find("form")
    submit_url = urljoin(url, form_tag.get("action")) if form_tag else url

    return answer, submit_url


# ------------------------------------------------------------
# ROOT
# ------------------------------------------------------------
@app.get("/")
async def root():
    return {"service": "I am here", "status": "OK"}


# ------------------------------------------------------------
# RECEIVE (MAIN)
# ------------------------------------------------------------
@app.post("/receive")
async def receive(request: Request):
    try:
        data = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if data.get("secret") != GOOGLE_FORM_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden: secret mismatch")

    try:
        current_url = data["url"]

        # Extract master JSON on first page
        master_payload = await payme(current_url)

        chain = []
        payloads = []

        while current_url:
            answer, next_url = await solve_quiz(current_url)

            # Extract answer text
            if isinstance(answer, dict):
                try:
                    g = answer["output"][0]["content"][0]["text"]
                except:
                    g = "0"
            else:
                g = str(answer)

            chain.append({"url": current_url, "answer": g})

            current_url = next_url

        return {
            "status": "done",
            "chain": chain,
            "payload": payloads
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))