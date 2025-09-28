# AutoClipsBot

Simple FastAPI-based service that:
- Downloads a provided YouTube (or supported) URL
- Detects scenes (PySceneDetect)
- Creates short clips (FFmpeg)
- Optionally transcribes clips (Whisper)
- Generates suggested title/description/hashtags (Gemini stub / API)

## Quick start (Docker)
1. Build:

docker build -t autoclipsbot:latest .

2. Run:

docker run --rm -p 8000:8000 -e PORT=8000 -e WHISPER_MODEL=small -e OUTPUT_DIR=/app/outputs autoclipsbot:latest

3. Call:

curl -X POST "http://localhost:8000/process" -H "Content-Type: application/json" -d '{"url":"https://www.youtube.com/watch?v=VIDEO_ID","max_clips":2}'

## Deploy to Render
- Push repo to GitHub, create new Web Service on Render, connect repo. Use `render.yaml` or set Build/Start commands:
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

## Notes
- Use content you own or have rights to monetize.
- Whisper models can be heavy. `small` recommended for CPU; consider cloud ASR for scale.
- Configure GEMINI_API_KEY in environment to enable title/description generation via Gemini REST; otherwise fallback heuristics used.


---

Extra tips & small checklist before deploy

1. If openai-whisper or torch creates heavy image sizes, try using smaller Whisper models (base, small).


2. Confirm ffmpeg works inside container: ffmpeg -version.


3. For YouTube uploading/auto publishing you'll need YouTube Data API OAuth flow — I can add that later.


4. For Render free plan, long video processing could hit request timeouts — better to accept job and run background worker or queue (Redis + Celery / RQ). For now this is synchronous and OK for testing.


5. If Gemini API endpoint/format changes, update call_gemini_api accordingly.
