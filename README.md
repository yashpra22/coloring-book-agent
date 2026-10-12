# Daily Kids Coloring Book Agent

Automated agentic framework that generates a **101-page A4 PDF coloring book** (1 AI cover + 100 coloring pages) daily for kids. Uses free cloud APIs.

## Architecture

```
main.py ──────────────┐
                       ├── agents/prompt_agent.py   (LLM generates creative prompts)
                       ├── agents/image_agent.py    (Cloudflare Workers AI generates images;
                       │                             Pollinations / NVIDIA / HuggingFace
                       │                             providers kept for future use)
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

You need:
- `OPENROUTER_API_KEY` — creative prompt generation (optional, templates work too)
- `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN` — **primary image generation**
- `NVIDIA_API_KEY` / `HF_TOKEN` — optional future fallbacks (kept, currently inactive)

### 3. Test (Dry Run)
```bash
python main.py --dry-run --pages 5
```

### 4. Generate a Book
```bash
python main.py                    # Full 100-page book
python main.py --pages 20         # Quick 20-page test
```

## Image Providers

| Provider | Status | Notes |
|----------|--------|-------|
| Cloudflare Workers AI | ✅ Active (primary) | Free 10k neurons/day, SDXL-Lightning |
| Pollinations.ai | 🔒 Kept for future | Code + config intact, enable in `provider_priority` |
| NVIDIA NIM | 🔒 Kept for future | Needs SDXL function enabled on account |
| Hugging Face | 🔒 Kept for future | Needs paid inference credits for FLUX |

> **Note:** Only Cloudflare is active right now. Re-enable others in
> `config/settings.yaml` → `generation.provider_priority` when a good
> free image model is available.

## Free API Keys

| Service | Purpose | Get Key |
|---------|---------|---------|
| OpenRouter | LLM prompts | https://openrouter.ai/keys |
| Cloudflare | Image gen (primary) | https://dash.cloudflare.com/?to=/:account/ai |
| NVIDIA NIM | Image gen (future) | https://build.nvidia.com/ |
| Hugging Face | Image gen (future) | https://huggingface.co/settings/tokens |

## Daily Automation

### Option A: GitHub Actions (Cloud)
1. Push this repo to GitHub
2. Add secrets in Settings > Secrets > Actions:
   - `OPENROUTER_API_KEY`
   - `CLOUDFLARE_ACCOUNT_ID`
   - `CLOUDFLARE_API_TOKEN`
   - `NVIDIA_API_KEY` (optional, future)
   - `HF_TOKEN` (optional, future)
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
├── run.bat                          # Double-click to run (Windows)
├── requirements.txt
├── .env.example
├── config/
│   ├── settings.yaml                # All configuration
│   └── themes.yaml                  # Theme pool for variety
├── agents/
│   ├── prompt_agent.py              # LLM prompt generation
│   ├── image_agent.py               # Multi-provider image generation
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
