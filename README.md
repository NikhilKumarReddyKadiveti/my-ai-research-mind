# ResearchMind AI

ResearchMind AI is a privacy-first research and tutor assistant. Its main purpose is to help users find the best free learning resources, read public pages/documents/videos where possible, summarize them, and turn them into step-by-step learning plans.

OpenAI can be used as a server-side helper API, but the long-term goal remains building and improving your own ResearchMind language model.

## Features

- **Custom SLM:** Transformer-based Small Language Model training code in PyTorch.
- **Research Agent:** Web research using DuckDuckGo and scraping.
- **Resource Reader:** Reads public pages, PDFs, and YouTube transcripts when available.
- **Research Tutor:** Finds free resources, summarizes them, explains why each resource is useful, and creates learning steps.
- **RAG System:** Retrieval-Augmented Generation using ChromaDB and Sentence Transformers.
- **OpenAI Assistant API:** Backend-only OpenAI integration for authenticated AI chat.
- **Voice Action API:** Converts instructions into browser, phone dialer, and WhatsApp links with user confirmation.
- **Supabase Auth:** Email/password and Google OAuth-ready login.
- **Supabase Security:** Row Level Security policies so each user can access only their own rows.
- **Universal App:** Expo app for web, Android, and iOS from one shared codebase.
- **FastAPI Backend:** API layer for auth-verified AI, research, tutoring, maps, and actions.

## Security First

Rotate any OpenAI key that has been pasted into chat or committed anywhere. The OpenAI key must only be placed in `backend/.env`, never inside the Expo app, web app, or Supabase SQL.

The local `.env` files include your Supabase project URL and anon key, but the OpenAI key is intentionally left as a placeholder until you create a fresh rotated key.

The `/voice-action` endpoint does not store command history, contact names, phone numbers, messages, microphone audio, browser history, or device data. Phone calls and WhatsApp messages require the user to confirm the final call/send action on their device.

## Project Structure

```text
researchmind-ai/
  apps/
    researchmind-universal/  Expo web, Android, and iOS app
  agent/                     Research, tutoring, RAG, maps, and action agents
  backend/                   FastAPI backend
  frontend/                  Simple browser voice-action test page
  model/                     Custom SLM and training
  supabase/                  SQL schema and RLS policies
  docker-compose.yml
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
OPENAI_API_KEY=your_rotated_openai_key
OPENAI_MODEL=gpt-5-mini
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
FRONTEND_ORIGINS=http://localhost:8081,http://localhost:19006,http://127.0.0.1:8081
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

- `GET /` public health check
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

## Deployment

Use `docker-compose.yml` as a starting point, but set real production environment variables and restrict CORS before deploying.
