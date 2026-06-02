import pandas as pd
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
import json
import os

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}



