import os
import time
import base64
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

app = FastAPI(title="PSG Tech Mess Menu API")

# Swap "*" for your real Netlify domain once you know it, e.g.
# ["https://psg-mess.netlify.app"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# /rate-submit
# ---------------------------------------------------------------------------
class RatingIn(BaseModel):
    user_id: str
    score: str          # kept as string to match the app's existing payload shape
    comment: Optional[str] = ""
    mess: Optional[str] = None
    day: Optional[str] = None
    meal: Optional[str] = None


@app.post("/rate-submit")
async def rate_submit(payload: RatingIn):
    try:
        score_int = int(payload.score)
    except ValueError:
        raise HTTPException(status_code=400, detail="score must be a number 1-5")
    if not (1 <= score_int <= 5):
        raise HTTPException(status_code=400, detail="score must be between 1 and 5")

    supabase.table("ratings").insert({
        "user_id": payload.user_id,
        "mess": payload.mess,
        "day": payload.day,
        "meal": payload.meal,
        "score": score_int,
        "comment": payload.comment or "",
    }).execute()
    return {"ok": True}


# ---------------------------------------------------------------------------
# /complaint-submit
# ---------------------------------------------------------------------------
class ComplaintIn(BaseModel):
    mess: str
    comment: str
    photo: Optional[str] = None  # data URL, e.g. "data:image/jpeg;base64,...."


@app.post("/complaint-submit")
async def complaint_submit(payload: ComplaintIn):
    if not payload.comment.strip():
        raise HTTPException(status_code=400, detail="comment is required")

    photo_url = None
    if payload.photo:
        try:
            header, b64data = payload.photo.split(",", 1)
            content = base64.b64decode(b64data)
            filename = f"{int(time.time())}_{os.urandom(4).hex()}.jpg"
            supabase.storage.from_("complaint-photos").upload(
                filename, content, {"content-type": "image/jpeg"}
            )
            photo_url = supabase.storage.from_("complaint-photos").get_public_url(filename)
        except Exception:
            # Don't fail the whole complaint just because the photo upload broke.
            photo_url = None

    supabase.table("complaints").insert({
        "mess": payload.mess,
        "comment": payload.comment,
        "photo_url": photo_url,
    }).execute()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Health check (useful for Render/Railway to confirm the service is alive)
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}
