# Deploy Bharatiyam AI Chatbot

## Quick deploy options

### Option 1: Railway (recommended for beginners)
1. Push this repo to GitHub
2. Connect Railway to your GitHub
3. New Project → Add GitHub repo
4. Set environment variables in Railway dashboard (see .env.example)
5. Deploy → Railway will build Dockerfile and expose port 8000

### Option 2: Render
1. Push to GitHub
2. New Web Service → Connect GitHub
3. Build Command: `uvicorn app.api:app --host 0.0.0.0 --port $PORT`
4. Add env vars from .env.example
5. Deploy

### Option 3: Vercel (serverless)
1. Push to GitHub
2. New Project → Connect GitHub
3. Build Settings → Override:
   - Output Directory: `.`
   - Install Command: `pip install -r requirements.txt`
   - Build Command: `echo "Skip build for serverless"`
   - Start Command: `uvicorn app.api:app --host 0.0.0.0 --port $PORT`
4. Add env vars
5. Deploy

### Option 4: Fly.io
1. Install Fly CLI
2. `fly launch --no-deploy` to generate fly.toml
3. Set secrets: `fly secrets set GROQ_API_KEY=...`
4. `fly deploy`

## Environment variables required
- `MONGO_URI` (MongoDB connection string)
- `DB_NAME`
- `GROQ_API_KEY`
- `GROQ_MODEL`
- `EMBED_MODEL`

## After deployment
1. Note the public URL (e.g., `https://bhartiyam-api.onrender.com`)
2. Update your Virasat frontend env:
   ```
   VITE_BHARTIYAM_API_URL=https://bhartiyam-api.onrender.com
   ```
3. Redeploy Virasat frontend

## CORS
The FastAPI app already allows:
- `https://virasat-shetty.onrender.com`
- `https://your-bhartiyam-domain.com`
- `"*"` fallback for dev

## Health check
- `GET /` returns `{"message":"Bharatiyam AI Assistant API is running"}`
- Use this to verify deployment is live
