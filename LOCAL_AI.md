# ResearchMind Local AI

ResearchMind now supports three AI paths:

1. Gemini for online high-quality original reasoning.
2. Ollama-compatible local models for offline/dev use.
3. The scratch ResearchMind SLM as a training project and emergency fallback.

## Recommended Local Setup

For 16 GB RAM and a 4 GB RTX 2050, start with small quantized models:

```bash
ollama pull qwen2.5-coder:3b
ollama pull llama3.2:3b
```

Use the coding model for development:

```bash
python researchmind_cli.py --provider ollama --model qwen2.5-coder:3b code "build a FastAPI todo endpoint"
```

Use Gemini for stronger online reasoning:

```bash
python researchmind_cli.py --provider gemini chat "explain transformers simply"
```

Interactive chat:

```bash
python researchmind_cli.py chat
```

## Environment

Set these in `backend/.env`:

```bash
AI_PROVIDER=auto
GEMINI_MODEL=gemini-2.5-flash
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5-coder:3b
```

`AI_PROVIDER=auto` tries Gemini first, then local Ollama, then the simple built-in fallback.

## About The Scratch SLM

The custom PyTorch model in `model/` is useful for learning and experiments, but it will not match Gemini or modern local models without a large dataset, long training, instruction tuning, and evaluation. Keep it as the ResearchMind-owned model path while using Gemini/Ollama for real productivity.

## Training From Your ResearchMind Chats

In the website, open `Settings` and click `Export chats for local AI training`. Then run:

```powershell
python researchmind_cli.py ingest-training path\to\researchmind-training-YYYY-MM-DD.json
python researchmind_cli.py train-local --iters 500
```

If your chats are already saved in Supabase, you can pull them with a current user access token:

```powershell
python researchmind_cli.py pull-training --access-token YOUR_SUPABASE_USER_TOKEN --limit 500
python researchmind_cli.py train-local --iters 500
```

`pull-training` reads from `messages`, `learning_sessions`, and `learning_resources`, so tutor lessons and research resources become part of the local training text too.

To train automatically when you log in to Windows, run this once from PowerShell:

```powershell
.\scripts\install_train_on_login.ps1
```

The scheduled task trains from `model/data/train_data.txt`, so export or pull fresh chats before expecting the local model to learn new behavior.
