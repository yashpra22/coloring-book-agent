# Daily Kids Coloring Book Agent

Automated agentic framework that generates a **101-page A4 PDF coloring book** (1 AI cover + 100 coloring pages) daily for kids. Uses free cloud APIs.

## Architecture

```
main.py ──────────────┐
                       ├── agents/prompt_agent.py   (LLM generates creative prompts)
                       ├── agents/image_agent.py    (NVIDIA/HF model APIs generate images)
                       ├── agents/process_agent.py  (OpenCV converts to clean line art)
                       └── agents/pdf_agent.py      (fpdf2 assembles A4 PDF)
```

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Keys
```bash
copy .env.example .env
# Edit .env and add your keys
```

### 3. Test (Dry Run)
```bash
python main.py --dry-run --pages 5
```

### 4. Generate a Book
```bash
python main.py                    # Full 100-page book
python main.py --pages 20         # Quick 20-page test
```

## Free API Keys (Optional)

| Service | Purpose | Free Tier | Get Key |
|---------|---------|-----------|---------|
| OpenRouter | LLM prompts | Unlimited free models | https://openrouter.ai/keys |
| NVIDIA NIM | Image gen | Free tier | https://build.nvidia.com/ |
| Hugging Face | Image gen | 30k req/month | https://huggingface.co/settings/tokens |

> **Note:** Image generation now requires either `NVIDIA_API_KEY` or `HF_TOKEN`. Prompt generation can still fall back to templates if OpenRouter is unavailable.

## Daily Automation

### Option A: GitHub Actions (Cloud)
1. Push this repo to GitHub
2. Add secrets in Settings > Secrets > Actions:
   - `OPENROUTER_API_KEY`
   - `NVIDIA_API_KEY`
   - `HF_TOKEN`
3. The workflow runs daily at 6 AM UTC automatically
4. PDFs are saved as artifacts and committed to the repo

### Option B: Windows Task Scheduler (Local)
```powershell
# Run as Administrator
powershell -ExecutionPolicy Bypass -File scripts/setup_windows_task.ps1
```

## Project Structure

```
coloring-book-agent/
├── main.py                          # Main orchestrator
├── run_local.py                     # Windows local entry
├── run.bat                          # Double-click to run
├── requirements.txt
├── .env.example
├── config/
│   ├── settings.yaml                # All configuration
│   └── themes.yaml                  # Theme pool for variety
├── agents/
│   ├── prompt_agent.py              # LLM prompt generation
│   ├── image_agent.py               # Multi-API image generation
│   ├── process_agent.py             # Line art processing
│   ├── pdf_agent.py                 # PDF assembly
│   └── utils.py                     # Shared utilities
├── scripts/
│   └── setup_windows_task.ps1       # Windows scheduler setup
├── .github/
│   └── workflows/
│       └── daily-generation.yml     # GitHub Actions
├── output/
│   ├── raw/                         # Raw generated images
│   ├── processed/                   # Processed line art
│   ├── books/                       # Final PDFs
│   └── prompts/                     # Saved prompts JSON
└── logs/
```

## Output

Each run produces:
- `output/books/coloring_book_YYYY-MM-DD_Title.pdf` — The final A4 PDF
- `output/prompts/prompts_YYYY-MM-DD.json` — All generated prompts
- `output/raw/` — Raw AI images (before processing)
- `output/processed/` — Clean line art images
