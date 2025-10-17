import io
import os
from typing import Optional, List
import numpy as np
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    import pyreadstat
except Exception:
    pyreadstat = None

try:
    import statsmodels.api as sm
except Exception as e:
    sm = None

app = FastAPI(title="BRFSS 2023 – T2D Analyzer API", version="0.1.0")

# CORS for local dev (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Helpers ----------------
def read_any(content: bytes, filename: str) -> pd.DataFrame:
    name = filename.lower()
    bio = io.BytesIO(content)
    if name.endswith(".csv"):
        return pd.read_csv(bio, low_memory=False)
    if name.endswith(".parquet"):
        return pd.read_parquet(bio)
    if name.endswith(".xpt") or name.endswith(".xport"):
        if pyreadstat is None:
            raise RuntimeError("pyreadstat is required for .xpt files")
        df, meta = pyreadstat.read_xport(bio)
        return df
    raise ValueError("Unsupported file type. Use .csv, .parquet, or .xpt")

def recode_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    cols = {c.lower(): c for c in out.columns}
    def col(name): return cols.get(name.lower())

    diab = col("DIABETE4")
    predi1 = col("PDIABTS1")
    predi2 = col("PREDIAB2")

    def cat_row(row):
        v = row.get(diab)
        if pd.isna(v): return np.nan
        try:
            v = int(v)
        except Exception:
            return np.nan
        if v == 1: return "Diabetes"
        if v == 3: return "Gestational only"
        if v in (2, 4):
            p1 = row.get(predi1)
            p2 = row.get(predi2)
            for p in (p1, p2):
                try:
                    if int(p) == 1:
                        return "Prediabetes"
                except Exception:
                    pass
            return "No diabetes"
        return np.nan

    out["diabetes_cat"] = out.apply(cat_row, axis=1)
    out["t2d_binary"] = (out["diabetes_cat"] == "Diabetes").astype("float")

    bmi5 = col("_BMI5")
    if bmi5:
        out["BMI"] = pd.to_numeric(out[bmi5], errors="coerce") / 100.0
        out["BMI_cat"] = pd.cut(out["BMI"],
                                bins=[0, 18.5, 25, 30, np.inf],
                                labels=["Under", "Normal", "Over", "Obese"],
                                right=False)
    else:
        out["BMI"] = np.nan
        out["BMI_cat"] = np.nan

    ageg = col("_AGEG5YR"); sex = col("_SEX")
    if ageg: out["age_group"] = out[ageg]
    if sex:  out["sex"] = out[sex].map({1: "Male", 2: "Female"}).astype("object")

    return out

def weighted_mean(x: pd.Series, w: pd.Series) -> float:
    x, w = x.astype(float), w.astype(float)
    m = np.isfinite(x) & np.isfinite(w)
    if not m.any():
        return np.nan
    return (x[m] * w[m]).sum() / w[m].sum()

def weighted_prevalence(df: pd.DataFrame, by: Optional[str], weight_col: str, outcome: str="t2d_binary"):
    d = df.copy()
    if weight_col not in d.columns:
        d[weight_col] = 1.0
    if by is None:
        prev = weighted_mean(d[outcome].fillna(0), d[weight_col])
        return pd.DataFrame({"group": ["Overall"], "prev": [prev]})
    rows = []
    for k, sub in d.groupby(by, dropna=False):
        p = weighted_mean(sub[outcome].fillna(0), sub[weight_col])
        rows.append((k, p))
    res = pd.DataFrame(rows, columns=[by, "prev"]).rename(columns={by: "group"})
    return res.sort_values("prev", ascending=False)

def plot_bar(df: pd.DataFrame, x: str, y: str, title: str):
    fig, ax = plt.subplots(figsize=(8, 5))
    df = df.copy()
    df[x] = df[x].astype(str)
    ax.bar(df[x], df[y])
    ax.set_title(title)
    ax.set_ylabel("Proportion")
    ax.set_xlabel("")
    ax.set_ylim(0, max(0.01, df[y].max() * 1.15))
    for i, v in enumerate(df[y].values):
        ax.text(i, v + (0.01 * (df[y].max() if np.isfinite(df[y].max()) else 1.0)), f"{v:.3f}", ha='center', va='bottom', fontsize=9)
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=600, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf

# ---------------- Endpoints ----------------
@app.get("/health")
def health():
    return {"ok": True}

@app.post("/recode")
async def api_recode(file: UploadFile = File(...), weight_col: Optional[str] = Form(default="_LLCPWT")):
    content = await file.read()
    df = read_any(content, file.filename)
    rec = recode_outcomes(df)
    keep = ["diabetes_cat", "t2d_binary", "BMI", "BMI_cat", "age_group", "sex"]
    if weight_col not in rec.columns:
        rec[weight_col] = 1.0
    keep.append(weight_col)
    out = rec[[c for c in keep if c in rec.columns]].head(5000)  # cap rows for payload size
    return JSONResponse(out.to_dict(orient="records"))

@app.post("/prevalence")
async def api_prevalence(
    file: UploadFile = File(...),
    by: Optional[str] = Form(default=None),
    weight_col: Optional[str] = Form(default="_LLCPWT")
):
    content = await file.read()
    df = recode_outcomes(read_any(content, file.filename))
    res = weighted_prevalence(df, by=by, weight_col=(weight_col or "_LLCPWT"))
    return JSONResponse(res.to_dict(orient="records"))

@app.post("/plot/prevalence")
async def api_plot_prevalence(
    file: UploadFile = File(...),
    by: Optional[str] = Form(default=None),
    weight_col: Optional[str] = Form(default="_LLCPWT")
):
    content = await file.read()
    df = recode_outcomes(read_any(content, file.filename))
    res = weighted_prevalence(df, by=by, weight_col=(weight_col or "_LLCPWT"))
    title = "T2D prevalence" + (f" by {by}" if by else " (overall)")
    buf = plot_bar(res, x="group", y="prev", title=title)
    return StreamingResponse(buf, media_type="image/png")

@app.post("/logit")
async def api_logit(
    file: UploadFile = File(...),
    covars_csv: Optional[str] = Form(default=""),
    weight_col: Optional[str] = Form(default="_LLCPWT")
):
    if sm is None:
        return JSONResponse({"error": "statsmodels not installed"}, status_code=400)
    content = await file.read()
    df = recode_outcomes(read_any(content, file.filename))
    d = df.copy()
    if weight_col not in d.columns:
        d[weight_col] = 1.0
    covars = [c.strip() for c in (covars_csv or "").split(",") if c.strip()]
    if not covars:
        covars = []
        if "BMI_cat" in d.columns: covars.append("C(BMI_cat)")
        if "age_group" in d.columns: covars.append("C(age_group)")
        if "sex" in d.columns: covars.append("C(sex)")
    formula = "t2d_binary ~ " + " + ".join(covars) if covars else "t2d_binary ~ 1"
    model = sm.GLM.from_formula(formula, data=d, family=sm.families.Binomial(), freq_weights=d.get(weight_col, 1.0))
    res = model.fit()
    tab = res.summary2().tables[1].reset_index().rename(columns={"index": "term"})
    tab["OR"] = np.exp(tab["Coef."])
    tab["OR_low"] = np.exp(tab["Coef."] - 1.96 * tab["Std.Err."])
    tab["OR_high"] = np.exp(tab["Coef."] + 1.96 * tab["Std.Err."])
    tbl = tab[["term", "OR", "OR_low", "OR_high", "P>|z|"]]
    return {"formula": formula, "table": tbl.to_dict(orient="records")}
