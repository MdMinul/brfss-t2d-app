# Backend (FastAPI)

## Run locally
```bash
pip install -r backend/requirements.txt
uvicorn main:app --app-dir backend --reload --port 8000
```

## Endpoints
- `GET /health`
- `POST /recode` (multipart: `file`, form: `weight_col`)
- `POST /prevalence` (multipart: `file`, form: `by`, `weight_col`)
- `POST /plot/prevalence` (multipart: `file`, form: `by`, `weight_col`) → PNG (600 dpi)
- `POST /logit` (multipart: `file`, form: `covars_csv`, `weight_col`) → OR table

> Note: Uses final weights (`_LLCPWT`). Full complex-survey variance not included.
