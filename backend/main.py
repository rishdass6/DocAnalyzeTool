from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")

print(api_key)

app = FastAPI()

@app.get("/health")
def get_health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port = 8000, reload = True)