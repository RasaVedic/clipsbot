# main.py
import os
import uuid
import json
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from utils import run_cmd, find_downloaded_file
import shutil

# Media / ML libs
try:
    import whisper
except Exception:
    whisper = None

from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector

load_dotenv()

# Config from env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./outputs")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
MAX_CLIP_SECONDS = int(os.getenv("MAX_CLIP_SECONDS", "60"))
MIN_CLIP_SECONDS = int(os.getenv("MIN_CLIP_SECONDS", "6"))

os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI(title="AutoClipsBot")

class ProcessRequest(BaseModel):
    url: str
    max_clips: int = 3
    prefer_vertical: bool = True

class ClipInfo(BaseModel):
    filename: str
    start: float
    end: float
    duration: float
    title: str = ""
    description: str = ""
    hashtags: List[str] = []
    transcript: str = ""

def download_video(url: str, out_dir: str) -> str:
    out_template = os.path.join(out_dir, "input.%(ext)s")
    cmd = ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best", "-o", out_template, url]
    run_cmd(cmd)
    fpath = find_downloaded_file(out_dir, prefix="input.")
    if not fpath:
        raise FileNotFoundError("Downloaded file not found after yt-dlp")
    return fpath

def detect_scenes(video_path: str) -> List[Dict[str, float]]:
    vm = VideoManager([video_path])
    sm = SceneManager()
    sm.add_detector(ContentDetector(threshold=30.0))
    try:
        vm.start()
        sm.detect_scenes(frame_source=vm)
        scene_list = sm.get_scene_list()
        scenes = []
        for start, end in scene_list:
            scenes.append({"start": start.get_seconds(), "end": end.get_seconds()})
        return scenes
    finally:
        vm.release()

def make_clip(input_path: str, out_path: str, start: float, end: float, prefer_vertical: bool = True):
    vf = None
    if prefer_vertical:
        vf = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
    cmd = ["ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", input_path]
    if vf:
        cmd += ["-vf", vf]
    cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac", "-b:a", "128k", out_path]
    run_cmd(cmd)

def transcribe_whisper(path: str) -> str:
    if whisper is None:
        return ""
    model = whisper.load_model(WHISPER_MODEL)
    res = model.transcribe(path)
    return res.get("text", "").strip()

def call_gemini_stub(transcript: str) -> Dict[str, Any]:
    """Fallback: no API key provided. Return simple heuristic metadata."""
    title = (transcript.strip().split("\n")[0][:70] + "...") if transcript else "Short clip"
    desc = (transcript[:200] + "...") if transcript else ""
    hashtags = ["#shorts", "#viral", "#clip"]
    return {"title": title, "description": desc, "hashtags": hashtags}

def call_gemini_api(transcript: str) -> Dict[str, Any]:
    """Placeholder for Gemini API call. Replace with real endpoint if available.
       Current implementation tries GEMINI_API_KEY; if missing returns stub.
    """
    if not GEMINI_API_KEY:
        return call_gemini_stub(transcript)

    # WARNING: Adjust endpoint/payload per Gemini/Google docs.
    endpoint = "https://api.ai.google/v1/models/gemini-2.0-flash:generateText"
    headers = {"Authorization": f"Bearer {GEMINI_API_KEY}", "Content-Type": "application/json"}
    prompt = (
        "You are a social media assistant. From the transcript below produce a JSON with keys:\n"
        "title (5-8 words), description (one sentence), hashtags (list of strings)\n\n"
        f"Transcript:\n{transcript}\n\nRespond ONLY in JSON."
    )
    payload = {"prompt": prompt, "max_output_tokens": 256}
    import requests
    resp = requests.post(endpoint, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        return call_gemini_stub(transcript)
    try:
        out_text = resp.text
        # try to parse first JSON object in text
        start = out_text.find("{")
        end = out_text.rfind("}")
        if start != -1 and end != -1:
            j = json.loads(out_text[start:end+1])
            # normalize tags
            tags = j.get("hashtags", j.get("tags", []))
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.replace("#", "").split(",") if t.strip()]
            return {"title": j.get("title",""), "description": j.get("description",""), "hashtags": tags}
    except Exception:
        pass
    return call_gemini_stub(transcript)

@app.post("/process", response_model=List[ClipInfo])
def process(req: ProcessRequest):
    jobid = str(uuid.uuid4())[:8]
    jobdir = os.path.join(OUTPUT_DIR, jobid)
    os.makedirs(jobdir, exist_ok=True)
    try:
        input_path = download_video(req.url, jobdir)
        scenes = detect_scenes(input_path)
        if not scenes:
            # fallback: whole duration
            out, _ = run_cmd(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "default=noprint_wrappers=1:nokey=1", input_path])
            dur = float(out.strip())
            scenes = [{"start": 0.0, "end": dur}]

        # build candidates
        candidates = []
        for scene in scenes:
            s, e = scene["start"], scene["end"]
            d = max(0.0, e - s)
            if d < MIN_CLIP_SECONDS:
                continue
            if d > MAX_CLIP_SECONDS:
                cur = s
                while cur < e and len(candidates) < req.max_clips * 3:
                    nxt = min(cur + MAX_CLIP_SECONDS, e)
                    candidates.append({"start": cur, "end": nxt})
                    cur = nxt
            else:
                candidates.append({"start": s, "end": e})
            if len(candidates) >= req.max_clips * 3:
                break

        clip_results = []
        for idx, cand in enumerate(candidates):
            if len(clip_results) >= req.max_clips:
                break
            s, e = cand["start"], cand["end"]
            dur = e - s
            fname = f"clip_{idx+1}.mp4"
            outclip = os.path.join(jobdir, fname)
            make_clip(input_path, outclip, s, e, prefer_vertical=req.prefer_vertical)
            transcript = ""
            try:
                transcript = transcribe_whisper(outclip)
            except Exception:
                transcript = ""
            # score simple: word count
            if len(transcript.split()) == 0 and dur < 15:
                # skip silent small
                continue
            meta = call_gemini_api(transcript)
            clip_info = ClipInfo(
                filename=os.path.relpath(outclip, start=OUTPUT_DIR),
                start=s, end=e, duration=dur,
                title=meta.get("title",""),
                description=meta.get("description",""),
                hashtags=meta.get("hashtags", []),
                transcript=transcript
            )
            clip_results.append(clip_info)

        if not clip_results:
            raise HTTPException(status_code=400, detail="No valid clips generated")

        return clip_results

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}")
