import React, { useMemo, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

type PrevRow = { group: string; prev: number }
type ORRow = { term: string; OR: number; OR_low: number; OR_high: number; ['P>|z|']: number }

export default function App() {
  const [file, setFile] = useState<File | null>(null)
  const [by, setBy] = useState<string>('')
  const [covars, setCovars] = useState<string>('')
  const [weightCol, setWeightCol] = useState<string>('_LLCPWT')
  const [prevRows, setPrevRows] = useState<PrevRow[] | null>(null)
  const [orRows, setOrRows] = useState<ORRow[] | null>(null)
  const [plotUrl, setPlotUrl] = useState<string>('')
  const [busy, setBusy] = useState(false)

  const canRun = useMemo(() => !!file, [file])

  const runPrev = async () => {
    if (!file) return
    setBusy(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      if (by) fd.append('by', by)
      if (weightCol) fd.append('weight_col', weightCol)
      const res = await fetch(`${API_BASE}/prevalence`, { method: 'POST', body: fd })
      const data = await res.json()
      setPrevRows(data)
      // Plot
      const plotFD = new FormData()
      plotFD.append('file', file)
      if (by) plotFD.append('by', by)
      if (weightCol) plotFD.append('weight_col', weightCol)
      const plotRes = await fetch(`${API_BASE}/plot/prevalence`, { method: 'POST', body: plotFD })
      const blob = await plotRes.blob()
      setPlotUrl(URL.createObjectURL(blob))
    } finally {
      setBusy(false)
    }
  }

  const runLogit = async () => {
    if (!file) return
    setBusy(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      if (covars) fd.append('covars_csv', covars)
      if (weightCol) fd.append('weight_col', weightCol)
      const res = await fetch(`${API_BASE}/logit`, { method: 'POST', body: fd })
      const data = await res.json()
      setOrRows(data.table || null)
    } finally {
      setBusy(false)
    }
  }

  const runRecode = async () => {
    if (!file) return
    setBusy(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      if (weightCol) fd.append('weight_col', weightCol)
      const res = await fetch(`${API_BASE}/recode`, { method: 'POST', body: fd })
      const data = await res.json()
      // Show a tiny preview of first 10
      alert(`Recode done. Preview rows: ${data.length}. Showing first 1: \n` + JSON.stringify(data[0], null, 2))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ fontFamily: 'Inter, system-ui, sans-serif', padding: 24, maxWidth: 1100, margin: '0 auto' }}>
      <h1>BRFSS 2023 – Type 2 Diabetes Analyzer (React + FastAPI)</h1>
      <p style={{ color: '#475569' }}>Upload a BRFSS dataset (.csv/.parquet/.xpt), choose tasks, and view results.</p>

      <section style={{ marginTop: 24, padding: 16, border: '1px solid #e2e8f0', borderRadius: 16 }}>
        <h2>1) Load Data</h2>
        <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        <div style={{ marginTop: 8, fontSize: 12, color: '#64748b' }}>
          Tip: Parquet loads fastest. XPT requires pyreadstat on the server.
        </div>
      </section>

      <section style={{ marginTop: 24, padding: 16, border: '1px solid #e2e8f0', borderRadius: 16 }}>
        <h2>2) Options</h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, maxWidth: 600 }}>
          <label>Group by (for prevalence): <input placeholder="age_group or sex" value={by} onChange={(e) => setBy(e.target.value)} /></label>
          <label>Weight col: <input value={weightCol} onChange={(e) => setWeightCol(e.target.value)} /></label>
          <label style={{ gridColumn: 'span 2' }}>Covariates (CSV): <input placeholder="C(BMI_cat), C(age_group), C(sex)" value={covars} onChange={(e) => setCovars(e.target.value)} /></label>
        </div>
      </section>

      <section style={{ marginTop: 24, padding: 16, border: '1px solid #e2e8f0', borderRadius: 16 }}>
        <h2>3) Run Tasks</h2>
        <div style={{ display: 'flex', gap: 12 }}>
          <button disabled={!canRun || busy} onClick={runRecode}>Recode outcomes</button>
          <button disabled={!canRun || busy} onClick={runPrev}>Weighted prevalence + plot</button>
          <button disabled={!canRun || busy} onClick={runLogit}>Logistic regression</button>
        </div>
      </section>

      <section style={{ marginTop: 24, padding: 16, border: '1px solid #e2e8f0', borderRadius: 16 }}>
        <h2>4) Results</h2>
        {prevRows && (
          <div>
            <h3>Prevalence Table</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr><th style={{ textAlign: 'left' }}>group</th><th style={{ textAlign: 'left' }}>prev</th></tr>
              </thead>
              <tbody>
                {prevRows.map((r, i) => (
                  <tr key={i}><td>{String(r.group)}</td><td>{r.prev.toFixed(3)}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {plotUrl && (
          <div style={{ marginTop: 12 }}>
            <h3>Prevalence Plot (600 dpi)</h3>
            <img src={plotUrl} alt="prevalence" style={{ maxWidth: '100%', borderRadius: 8, border: '1px solid #e2e8f0' }} />
          </div>
        )}

        {orRows && (
          <div style={{ marginTop: 12 }}>
            <h3>Logistic Regression (Odds Ratios)</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr><th>term</th><th>OR</th><th>95% CI</th><th>p</th></tr>
              </thead>
              <tbody>
                {orRows.map((r, i) => (
                  <tr key={i}>
                    <td>{r.term}</td>
                    <td>{r.OR.toFixed(2)}</td>
                    <td>{r.OR_low.toFixed(2)}–{r.OR_high.toFixed(2)}</td>
                    <td>{r['P>|z|'].toExponential(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
