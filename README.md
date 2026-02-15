# Normate AI

> AI-powered UX research synthesis — fuse quantitative and qualitative data into ranked, actionable recommendations in under 60 seconds.

Named after [Don Norman](https://en.wikipedia.org/wiki/Don_Norman), who coined the term "user experience."

---

## Architecture

```
┌──────────────────┐         ┌──────────────────────┐
│  Next.js 14 App  │  REST   │   FastAPI Backend     │
│  (Vercel)        │◄───────►│   (Railway)           │
│                  │         │                       │
│  Upload UI       │         │  Quant Processor      │
│  Results Dashboard│        │  Qual Processor       │
│  PDF Export      │         │  Fusion Engine        │
└──────────────────┘         │  Claude Integration   │
                             └───────┬──────────────┘
                                     │
                             ┌───────▼──────────────┐
                             │  Supabase             │
                             │  Auth · Job Storage   │
                             └──────────────────────┘
```

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.10+
- A Supabase project (free tier works)

### 1. Clone and install frontend

```bash
cd frontend
npm install
```

### 2. Configure frontend environment

```bash
cp .env.example .env.local
# Edit .env.local with your values
```

### 3. Install backend

```bash
cd backend
"C:\Users\prade\AppData\Local\Programs\Python\Python312\python.exe" -m venv venv
source venv/bin/activate  # Windows: venv/Scripts/activate
pip install -r requirements.txt
```

### 4. Configure backend environment

```bash
cp .env.example .env
# Edit .env with your values
```

### 5. Run both servers

**Terminal 1 — Frontend (port 3000):**
```bash
cd frontend
npm run dev
```

**Terminal 2 — Backend (port 8000):**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

Open [http://localhost:3000](http://localhost:3000)

---

## Environment Variables

### Frontend (`frontend/.env.local`)

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend URL, e.g. `http://localhost:8000` |

### Backend (`backend/.env`)

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key from console.anthropic.com |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Supabase anon/service key |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins |

---

## Project Structure

```
normate-ai/
├── frontend/
│   ├── app/
│   │   ├── layout.tsx          # Root layout + fonts + metadata
│   │   ├── page.tsx            # Landing / upload page
│   │   └── results/[jobId]/
│   │       └── page.tsx        # Results dashboard
│   ├── components/
│   │   ├── FileUpload.tsx      # Drag-and-drop file uploader
│   │   ├── ContextForm.tsx     # Research context form
│   │   ├── AnalyzeButton.tsx   # Submit button with states
│   │   ├── InsightCard.tsx     # Result insight display
│   │   └── Navbar.tsx          # Top navigation bar
│   ├── lib/
│   │   ├── api.ts              # Backend API client
│   │   └── utils.ts            # Shared utilities
│   └── public/
├── backend/
│   ├── main.py                 # FastAPI app entry
│   ├── routers/
│   │   └── analyze.py          # /api/analyze + /api/results
│   ├── services/
│   │   ├── quant_processor.py  # CSV/Excel analysis (Phase 2)
│   │   ├── qual_processor.py   # Text/DOCX analysis (Phase 2)
│   │   ├── fusion_engine.py    # Data fusion (Phase 2)
│   │   └── claude_service.py   # Claude API calls (Phase 2)
│   ├── models/
│   │   └── schemas.py          # Pydantic request/response models
│   └── requirements.txt
└── README.md
```

---

## Roadmap

- [x] **Phase 1** — Project setup, upload UI, FastAPI skeleton
- [ ] **Phase 2** — Quant processor, qual processor, fusion engine
- [ ] **Phase 3** — Claude integration, results dashboard
- [ ] **Phase 4** — PDF export, Supabase persistence, auth
- [ ] **Phase 5** — Polish, deploy, beta testing

---

## License

Private — all rights reserved.
