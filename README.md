# BRFSS 2023 – Type 2 Diabetes Analyzer (React + FastAPI)

Monorepo: `frontend` (Vite React + TS) and `backend` (FastAPI).

## Quick Start (local)

### 1) Backend
```bash
python -m venv .venv && source .venv/bin/activate  # (or .venv\Scripts\activate on Windows)
pip install -r backend/requirements.txt
uvicorn main:app --app-dir backend --reload --port 8000
```

### 2) Frontend
```bash
cd frontend
cp .env.example .env
# edit VITE_API_BASE if backend isn't localhost:8000
npm i
npm run dev
```

Open http://localhost:5173

## StackBlitz / GitHub
- **StackBlitz WebContainers** only run Node, not Python. So run the **frontend** on StackBlitz and point `VITE_API_BASE` to a hosted backend (Render, Railway, Fly.io, Hugging Face Spaces, or your own server/Docker).
- Deploy backend with Dockerfile or directly on a Python host.

## Features
- Upload `.csv / .parquet / .xpt` (SAS XPORT) or any file type you expose.
- Recode outcomes (`diabetes_cat`, `t2d_binary`, BMI/BMI_cat, age_group, sex) tuned for BRFSS 2023.
- Weighted prevalence (overall or by a grouping var) using `_LLCPWT` (fallback to uniform weights).
- 600 dpi PNG bar plot endpoint.
- Logistic regression (GLM Binomial w/ freq weights) returning ORs and 95% CIs.

> For full complex-survey variance estimation, consider an R backend (`survey` package) via `rpy2` or a separate microservice.
