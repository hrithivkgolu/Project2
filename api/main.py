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

@app.post("/receive")
async def receive(request: Request):
    data = await request.json()
    print("Received JSON:", data)

    return {
        "status": "success",
        "received": data
    }