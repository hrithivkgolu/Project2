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
#  Ask GPT (your AI pipe endpoint)
# ------------------------------------------------------------
def ask_chatgpt(task: str):
    url = "https://aipipe.org/openrouter/v1/responses"
    headers = {
        "Authorization": f"Bearer {AI_PIPE_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openai/gpt-4.1-nano",
        "input": f"""
You are an automated agent. Read the content below:

CONTENT:
{task}

Give ONLY one word as answer. If no answer, give 0.
"""
    }
    r = requests.post(url, json=payload, headers=headers)
    return r.json()


# ------------------------------------------------------------
# Extract JSON from <pre> on first quiz page
# ------------------------------------------------------------
async def payme(url: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "html.parser")
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
    except:
        return raw


# ------------------------------------------------------------
# Solve Based on Detected Quiz Type
# ------------------------------------------------------------
async def solve_quiz(url: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "html.parser")

    # ---------- QUIZ TYPE DETECTION ----------
    def detect_quiz_type():
        if soup.select_one("table"):
            return "scrape"
        if soup.select_one("audio"):
            return "audio"
        if soup.select_one("span.n1") or soup.select_one(".n1"):
            return "math"
        return "text"

    quiz_type = detect_quiz_type()

    # ---------- SCRAPE QUIZ ----------
    if quiz_type == "scrape":
        table = soup.select_one("table")
        rows = table.find_all("tr")
        extracted = []

        for tr in rows:
            cols = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if cols:
                extracted.append(cols)

        task_text = "\n".join([" | ".join(r) for r in extracted])
        answer = ask_chatgpt(task_text)

    # ---------- AUDIO QUIZ ----------
    elif quiz_type == "audio":
        audio_tag = soup.select_one("audio")
        audio_url = audio_tag.get("src")

        audio_url = urljoin(url, audio_url)

        async with httpx.AsyncClient() as client:
            audio_resp = await client.get(audio_url)
            audio_resp.raise_for_status()
            audio_bytes = audio_resp.content

        ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        result = ai.audio.transcriptions.create(
            file=("audio.wav", audio_bytes),
            model="gpt-4o-mini-tts"
        )
        transcript = result.text.strip()

        answer = ask_chatgpt(transcript)

    # ---------- MATH QUIZ ----------
    elif quiz_type == "math":
        n1 = soup.select_one(".n1, span.n1")
        n2 = soup.select_one(".n2, span.n2")

        try:
            a = int(n1.get_text(strip=True))
            b = int(n2.get_text(strip=True))
            return str(a + b), url
        except:
            return "0", url

    # ---------- TEXT QUIZ (#q / #question) ----------
    else:
        q = soup.select_one("#q") or soup.select_one("#question")
        quiz_text = q.get_text(strip=True) if q else ""
        answer = ask_chatgpt(quiz_text)

    # ---------- Extract Submit URL ----------
    form_tag = soup.find("form")
    submit_url = form_tag.get("action") if form_tag else url
    submit_url = urljoin(url, submit_url)

    return answer, submit_url


# ------------------------------------------------------------
#  ROOT ENDPOINT
# ------------------------------------------------------------
@app.get("/")
async def root():
    return {
        "service": "I am here",
        "status": "OK",
        "endpoint": "/receive (POST)"
    }


# ------------------------------------------------------------
#  RECEIVE ENDPOINT (MAIN LOGIC)
# ------------------------------------------------------------
@app.post("/receive")
async def receive(request: Request):
    try:
        data = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if "secret" not in data:
        raise HTTPException(status_code=400, detail="Missing 'secret' field")

    # check incoming secret
    if data["secret"] != GOOGLE_FORM_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden: secret mismatch")

    try:
        current_url = data["url"]
        collected = []
        payloads = []

        # First page: extract form JSON (contains correct secret)
        master_payload = await payme(current_url)

        while current_url:
            # Solve quiz
            answer, submit_url = await solve_quiz(current_url)

            # Extract ONE WORD from model output
            if isinstance(answer, dict):
                try:
                    g = answer["output"][0]["content"][0]["text"]
                except:
                    g = "0"
            else:
                g = str(answer)

            # Build payload per quiz:
            send_payload = {
                "email": master_payload["email"],
                "secret": master_payload["secret"],       # correct secret
                "url": current_url,
                "answer": g
            }

            payloads.append(send_payload)

            async with httpx.AsyncClient() as client:
                resp = await client.post(submit_url, json=send_payload)
                resp.raise_for_status()
                out = resp.json()
                collected.append(out)

            # Next quiz URL
            current_url = out.get("url")

        return JSONResponse(
            status_code=200,
            content={
                "status": "done",
                "chain": collected,
                "payload": payloads
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed: {str(e)}")