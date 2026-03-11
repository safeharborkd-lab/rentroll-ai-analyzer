# RentRoll AI Analyzer

Private equity-grade rent roll analysis for marina and real estate investors.

## Deploy to Streamlit Community Cloud (Recommended)

### Step 1: Push to GitHub

```bash
# From this directory
git init
git add .
git commit -m "Initial commit - RentRoll AI Analyzer"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/rentroll-ai-analyzer.git
git push -u origin main
```

### Step 2: Deploy

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click **"New app"**
4. Select your repo: `rentroll-ai-analyzer`
5. Branch: `main`
6. Main file path: `rentroll_ai_analyzer.py`
7. Click **Deploy**

Your app will be live at `https://your-app-name.streamlit.app` within ~2 minutes.

### Step 3: Custom Domain (Optional)

To use a subdomain like `rentroll.slipstreammarinas.com`:
- In Streamlit Cloud settings, add your custom domain
- In Cloudflare DNS, add a CNAME record pointing to the Streamlit URL

---

## Alternative: Run Locally

```bash
pip install -r requirements.txt
streamlit run rentroll_ai_analyzer.py
```

Opens at `http://localhost:8501`.

## Alternative: Self-Host on a VPS

```bash
# On a DigitalOcean / Railway / Render instance
pip install -r requirements.txt
streamlit run rentroll_ai_analyzer.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true
```

Put Cloudflare or nginx in front for HTTPS and auth.

---

## Repo Structure

```
rentroll-ai-analyzer/
├── .streamlit/
│   └── config.toml              # Theme + server config
├── rentroll_ai_analyzer.py      # Main app (1,750 lines)
├── requirements.txt             # Python dependencies
├── generate_sample_data.py      # Test data generator
├── sample_marina_portfolio.xlsx # 3-property marina test file
├── sample_multifamily.xlsx      # 66-unit MF test file
├── .gitignore
└── README.md
```

## Features

- **Auto Column Mapping** — handles marina (Slip #, LOA, Dock Fee) and MF (Unit #, SqFt, MR) formats
- **12 KPI Cards** — Occupancy, GPR, Economic Occupancy, Avg Rent/Unit, Avg Rent/SqFt, WALE, LTL%, Expirations
- **5 Tabs:**
  1. Summary & Charts (expiration waterfall, rent distribution, occupancy, rent vs size, revenue by type)
  2. Interactive Rent Roll Table (AgGrid with sort/filter/export)
  3. Tenant Concentration & Risk (top tenants, below-market flags)
  4. AI Insights (rules-based investment commentary)
  5. Seasonal Timing (marina monthly revenue curve, lease clustering, 18-month expiration exposure, property heatmap)
- **Sidebar Filters** — property, unit type, status, expiration bucket
- **Download Everything** — Excel, CSV, and TXT exports on every tab
