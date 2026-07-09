# ResearchMind AI

ResearchMind AI is a privacy-first research, tutor, and chat assistant. Its main purpose is to help users find useful learning resources, read public pages/documents/videos where possible, summarize them, and turn them into step-by-step learning conversations.

Gemini, OpenAI, and local models can be used as helper APIs, but the long-term goal remains building and improving your own ResearchMind language model from the user's learning and research data.

## Features

- **Custom SLM:** Transformer-based Small Language Model training code in PyTorch.
- **ResearchMind Website:** ChatGPT-style web UI with Chat, Research, Tutor, Settings, recent chat history, image upload/crop, and responsive layout.
- **AI Provider Settings:** Users can add their own Gemini/OpenAI API key in Settings or continue using the app's default backend AI.
- **Research Agent:** Web research using DuckDuckGo and scraping.
- **Resource Reader:** Reads public pages, PDFs, and YouTube transcripts when available.
- **Research Tutor:** Teaches topic by topic through chat, summarizes useful resources, explains why each resource matters, and creates learning steps.
- **RAG System:** Retrieval-Augmented Generation using ChromaDB and Sentence Transformers.
- **Gemini/OpenAI/Ollama AI Service:** Backend AI routing for online Gemini/OpenAI, local Ollama-compatible models, and simple local fallback.
- **CLI Assistant:** Local command-line interface for chat, tutoring, research, coding help, Supabase data pull, and local model training.
- **Voice Action API:** Converts instructions into browser, phone dialer, and WhatsApp links with user confirmation.
- **Supabase Auth:** Email/password and Google OAuth-ready login.
- **Supabase Memory:** Conversations, messages, tutor sessions, learning resources, progress, feedback, training runs, and checkpoints.
- **Supabase Security:** Row Level Security policies so each user can access only their own rows.
- **Universal App:** Expo app for web, Android, and iOS from one shared codebase.
- **FastAPI Backend:** API layer for AI chat, image chat, research, tutoring, maps, voice actions, auth checks, and static website serving.

## Security First

Rotate any Gemini/OpenAI key that has been pasted into chat or committed anywhere. Server-owned keys must only be placed in `backend/.env`, never inside the Expo app, web app source, or Supabase SQL.

The website lets a user store a personal API key in their own browser through Settings. That personal key is sent only with AI requests and is not saved in Supabase chat history.

The local `.env` files include your Supabase project URL and anon key, but server AI keys are intentionally left as placeholders until you create fresh rotated keys.

The `/voice-action` endpoint does not store command history, contact names, phone numbers, messages, microphone audio, browser history, or device data. Phone calls and WhatsApp messages require the user to confirm the final call/send action on their device.

## Project Structure

```text
researchmind-ai/
  apps/
    researchmind-universal/  Expo web, Android, and iOS app
  agent/                     Research, tutoring, RAG, maps, and action agents
  backend/                   FastAPI backend
  frontend/                  Main ResearchMind website UI
  model/                     Custom SLM and training
  scripts/                   Local helper scripts
  supabase/                  SQL schema and RLS policies
  docker-compose.yml
```

## Website

The main website lives in `frontend/` and is served by the FastAPI backend at:

```text
http://127.0.0.1:8000/
```

Current website pages:

- `Chat`: general AI assistant with recent conversation context.
- `Research`: asks the backend to search accessible web pages and write a source-based report.
- `Tutor`: teaches slowly, topic by topic, through the same chat system.
- `Settings`: sign in/out, delete selected chats, delete old history, export training data, view memory sync, and configure personal API keys.

The chat composer also supports:

- image upload inside the chat
- crop/select area before asking about an image
- microphone entry where browser speech recognition is available
- recent chat titles and suggestions from previous chats

## Personal API Keys

Users can open `Settings -> AI Provider` and choose:

- `Auto detect from key`
- `Gemini`
- `OpenAI`

If the user is signed in, the website saves the personal key through the backend as encrypted text in Supabase, then future devices can use it after login. The raw key is not returned to the browser after saving.

If the user is signed out, the key is stored only in that browser. If they clear it or leave it empty, the backend uses the app's configured default AI path:

1. Gemini when `GEMINI_API_KEY` is configured.
2. Ollama/local model when available.
3. Simple local fallback.

For existing Supabase projects, run this patch before using synced personal keys:

```text
supabase/schema_part_4_user_api_keys.sql
```

## Supabase SQL

Paste the full contents of this file into Supabase SQL Editor and run it:

```text
supabase/schema.sql
```

It creates:

- `profiles`
- `conversations`
- `messages`
- `user_security_settings`
- `learning_sessions`
- `learning_resources`
- `learning_steps`
- `resource_ingestion_jobs`
- `user_progress`
- `model_training_runs`
- `model_checkpoints`
- `feedback_events`
- triggers for new users and updated timestamps
- RLS policies for user-owned access

## Google Auth

In Supabase Dashboard:

1. Go to Authentication -> Providers -> Google.
2. Add your Google OAuth client ID and secret.
3. Add development redirects such as:

```text
http://localhost:8081
researchmind://auth/callback
```

Also configure the same local URL in your Google Cloud OAuth client while developing.

## Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Required `backend/.env` values:

```bash
AI_PROVIDER=auto
API_KEY_ENCRYPTION_SECRET=replace_with_a_long_random_secret_for_synced_user_keys
GEMINI_API_KEY=your_rotated_gemini_key
GEMINI_MODEL=gemini-2.5-flash
OPENAI_API_KEY=your_rotated_openai_key_optional
OPENAI_MODEL=gpt-5-mini
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5-coder:3b
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
FRONTEND_ORIGINS=http://localhost:8081,http://localhost:19006,http://127.0.0.1:8081,http://127.0.0.1:8000
```

After starting the backend, open:

```text
http://127.0.0.1:8000/
```

## Web, Android, And iOS App Setup

```bash
cd apps/researchmind-universal
npm install
npm run web
npm run android
npm run ios
```

Required Expo `.env` values:

```bash
EXPO_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
EXPO_PUBLIC_API_URL=http://127.0.0.1:8000
```

For Android emulator access to a backend running on your computer, you may need:

```bash
EXPO_PUBLIC_API_URL=http://10.0.2.2:8000
```

## API Endpoints

- `GET /` serves the ResearchMind website when `frontend/index.html` exists
- `GET /api/health` public health check
- `GET /api/config` public frontend config for Supabase and model labels
- `POST /assistant/chat` public website assistant endpoint with chat/research/tutor mode
- `POST /assistant/image` public website image assistant endpoint
- `GET /me` requires Supabase bearer token
- `POST /ai/chat` requires Supabase bearer token
- `POST /tutor/research` requires Supabase bearer token
- `POST /voice-action` requires Supabase bearer token
- `POST /research` research workflow
- `POST /navigate` maps workflow

## Custom Model Direction

The app is structured so OpenAI can help during development, but your own model can become the main brain over time. The database includes `model_training_runs` and `model_checkpoints` to track training, evaluation, active checkpoints, and future deployment.

To train the current custom model:

```bash
python model/data_collection.py
python model/data_cleaning.py
python model/train.py
```

The website can export chat history from Settings for local model training. The CLI can also pull Supabase messages, learning sessions, resources, steps, progress, and feedback into the training dataset:

```bash
python researchmind_cli.py ingest-training path/to/researchmind-training.json
python researchmind_cli.py pull-training --access-token YOUR_SUPABASE_USER_TOKEN
python researchmind_cli.py train-local --iters 500
```

## Deployment

The website frontend can be hosted on Netlify as static files, but AI features still need the FastAPI backend hosted separately.

Recommended production shape:

- Netlify: host `frontend/`
- Render/Railway/Fly.io/VPS: host `backend/`
- Supabase: auth and database
- Backend environment variables: Gemini/OpenAI/Supabase keys
- Frontend config: point requests to the deployed backend URL

Use `docker-compose.yml` as a starting point for self-hosting, but set real production environment variables and restrict CORS before deploying.
