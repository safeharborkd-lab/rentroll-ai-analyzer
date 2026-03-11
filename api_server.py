#!/usr/bin/env python3
"""RentRoll AI Analyzer — FastAPI Backend
Handles file upload (PDF/Excel/CSV), parsing, auto-cleanup, Claude AI flagging, KPIs, charts data, and export.
"""

import os
import re
import io
import json
import traceback
import uuid
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

import numpy as np
import pandas as pd
import pdfplumber
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional

# ─── Claude AI (Anthropic SDK) ───
try:
    from anthropic import Anthropic
    claude_client = Anthropic()
    HAS_CLAUDE = True
except Exception:
    HAS_CLAUDE = False


# ─── In-memory session store ───
# Keyed by visitor_id -> session data
sessions = {}


@asynccontextmanager
async def lifespan(app):
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def get_visitor(request: Request) -> str:
    return request.headers.get("x-visitor-id", "default")


# ════════════════════════════════════════════
# COLUMN MAPPING ENGINE
# ════════════════════════════════════════════

COLUMN_MAP = {
    "unit": {
        "patterns": [
            r"unit\s*#?", r"unit\s*num", r"unit\s*id", r"slip\s*#?",
            r"slip\s*num", r"space\s*#?", r"suite\s*#?", r"lot\s*#?",
            r"berth", r"dock\s*#?", r"bay\s*#?",
        ],
        "required": True,
    },
    "tenant": {
        "patterns": [
            r"tenant\s*name", r"tenant", r"tenancy", r"lessee", r"occupant",
            r"renter", r"customer", r"vessel\s*name", r"boat\s*name",
            r"owner\s*name", r"name", r"lease$",
        ],
        "required": False,
    },
    "monthly_rent": {
        "patterns": [
            r"monthly\s*rent", r"mr\b", r"rent\s*\/?\s*mo", r"mo\s*rent",
            r"monthly\s*rate", r"base\s*rent", r"contract\s*rent",
            r"current\s*rent", r"actual\s*rent", r"rent\s*amount",
            r"rent$", r"rate$", r"monthly\s*fee", r"slip\s*fee",
            r"storage\s*fee", r"dock\s*fee",
        ],
        "required": True,
    },
    "market_rent": {
        "patterns": [
            r"market\s*rent", r"market\s*rate", r"asking\s*rent",
            r"proforma\s*rent", r"pro\s*forma", r"comparable\s*rent",
            r"comp\s*rent", r"target\s*rent",
        ],
        "required": False,
    },
    "loa": {
        "patterns": [
            r"loa\b", r"length\s*overall", r"boat\s*length",
            r"slip\s*length", r"vessel\s*length", r"length\s*ft",
            r"size\s*ft", r"length", r"size",
        ],
        "required": False,
    },
    "sqft": {
        "patterns": [
            r"sq\s*ft", r"sqft", r"square\s*f", r"sf\b", r"rsf\b",
            r"area",
        ],
        "required": False,
    },
    "status": {
        "patterns": [
            r"status", r"occupancy\s*status", r"occ\s*status",
            r"vacant", r"occupied", r"lease\s*status", r"availability",
        ],
        "required": False,
    },
    "lease_start": {
        "patterns": [
            r"lease\s*start", r"start\s*date", r"commence",
            r"move\s*in", r"eff\s*date", r"effective\s*date",
        ],
        "required": False,
    },
    "lease_end": {
        "patterns": [
            r"lease\s*end", r"end\s*date", r"expir", r"expiry",
            r"maturity", r"term\s*end", r"move\s*out",
        ],
        "required": False,
    },
    "unit_type": {
        "patterns": [
            r"unit\s*type", r"type", r"category", r"class",
            r"bed\s*room", r"br\b", r"floorplan", r"floor\s*plan",
            r"slip\s*type", r"storage\s*type", r"wet\s*slip",
            r"dry\s*storage", r"covered",
        ],
        "required": False,
    },
    "property": {
        "patterns": [
            r"property", r"asset", r"building", r"location",
            r"site", r"marina\s*name", r"facility",
        ],
        "required": False,
    },
    "annual_rent": {
        "patterns": [
            r"annual\s*rent", r"yearly\s*rent", r"ar\b",
            r"rent\s*\/?\s*yr", r"yr\s*rent", r"annual\s*rate",
        ],
        "required": False,
    },
    "address": {
        "patterns": [
            r"address", r"home\s*address", r"street\s*address",
            r"mailing\s*address", r"addr",
        ],
        "required": False,
    },
    "zip_code": {
        "patterns": [
            r"zip\s*code", r"zip", r"postal\s*code", r"postal",
        ],
        "required": False,
    },
    "home_value": {
        "patterns": [
            r"home\s*value", r"redfin\s*estimate", r"zillow\s*estimate",
            r"property\s*value", r"home\s*price",
        ],
        "required": False,
    },
    "boat_make": {
        "patterns": [
            r"boat\s*make", r"make", r"manufacturer", r"brand",
            r"vessel\s*make",
        ],
        "required": False,
    },
    "boat_model": {
        "patterns": [
            r"boat\s*model", r"model", r"vessel\s*model",
        ],
        "required": False,
    },
    "boat_year": {
        "patterns": [
            r"boat\s*year", r"year\s*built", r"vessel\s*year", r"model\s*year",
        ],
        "required": False,
    },
}


def map_columns(df):
    mapping = {}
    used_cols = set()
    for field, cfg in COLUMN_MAP.items():
        best_match = None
        best_score = 0
        for col in df.columns:
            if col in used_cols:
                continue
            col_clean = str(col).strip().lower()
            for pattern in cfg["patterns"]:
                match = re.search(pattern, col_clean)
                if match:
                    coverage = (match.end() - match.start()) / max(len(col_clean), 1)
                    score = coverage * 1000 + len(pattern)
                    if score > best_score:
                        best_score = score
                        best_match = col
        if best_match:
            mapping[field] = best_match
            used_cols.add(best_match)
    return mapping


def clean_currency(series):
    if series.dtype in [np.float64, np.int64, float, int]:
        return series.astype(float)
    return (
        series.astype(str)
        .str.replace(r"[\$,\s]", "", regex=True)
        .str.replace(r"[()]", "-", regex=True)
        .str.strip()
        .replace(["", "-", "nan", "None", "N/A", "n/a"], np.nan)
        .astype(float)
    )


def clean_dataframe(df, mapping):
    clean = pd.DataFrame()
    if "unit" in mapping:
        clean["unit"] = df[mapping["unit"]].astype(str).str.strip()
    else:
        clean["unit"] = [f"Unit-{i+1}" for i in range(len(df))]

    if "tenant" in mapping:
        clean["tenant"] = df[mapping["tenant"]].astype(str).str.strip()
        clean["tenant"] = clean["tenant"].replace(["nan", "None", "", "N/A", "NaN"], "Vacant")
        # Detect VACANT in tenant/lease column
        vacant_mask = clean["tenant"].str.upper().str.contains("VACANT", na=False)
        clean.loc[vacant_mask, "tenant"] = "Vacant"
    else:
        clean["tenant"] = "Unknown"

    if "monthly_rent" in mapping:
        rent_col_name = str(mapping["monthly_rent"]).lower().strip()
        clean["monthly_rent"] = clean_currency(df[mapping["monthly_rent"]])
        # If the column name suggests annual rent, divide by 12
        if "annual" in rent_col_name or "yearly" in rent_col_name:
            clean["monthly_rent"] = clean["monthly_rent"] / 12
    elif "annual_rent" in mapping:
        clean["monthly_rent"] = clean_currency(df[mapping["annual_rent"]]) / 12
    else:
        clean["monthly_rent"] = 0.0

    if "market_rent" in mapping:
        clean["market_rent"] = clean_currency(df[mapping["market_rent"]])
    else:
        clean["market_rent"] = np.nan

    # LOA (Length Overall) — preferred for marinas
    if "loa" in mapping:
        clean["loa"] = clean_currency(df[mapping["loa"]])
    else:
        clean["loa"] = np.nan

    # SqFt — fallback for traditional real estate
    if "sqft" in mapping:
        clean["sqft"] = clean_currency(df[mapping["sqft"]])
    else:
        clean["sqft"] = np.nan

    # Address / Zip
    if "address" in mapping:
        clean["address"] = df[mapping["address"]].astype(str).str.strip()
        clean["address"] = clean["address"].replace(["nan", "None", ""], "")
    else:
        clean["address"] = ""

    if "zip_code" in mapping:
        clean["zip_code"] = df[mapping["zip_code"]].astype(str).str.strip().str[:5]
        clean["zip_code"] = clean["zip_code"].replace(["nan", "None", ""], "")
    elif "address" in mapping:
        # Extract last 5-digit number from address (zip code is at the end)
        clean["zip_code"] = clean["address"].str.extract(r'(\d{5})\s*$', expand=False).fillna("")
    else:
        clean["zip_code"] = ""

    # Home value
    if "home_value" in mapping:
        clean["home_value"] = clean_currency(df[mapping["home_value"]])
    else:
        clean["home_value"] = np.nan

    # Boat info
    for boat_field in ["boat_make", "boat_model", "boat_year"]:
        if boat_field in mapping:
            clean[boat_field] = df[mapping[boat_field]].astype(str).str.strip()
            clean[boat_field] = clean[boat_field].replace(["nan", "None", ""], "")
        else:
            clean[boat_field] = ""

    if "status" in mapping:
        raw_status = df[mapping["status"]].astype(str).str.strip().str.lower()
        clean["status"] = raw_status.apply(
            lambda x: "Vacant" if any(v in str(x) for v in ["vacant", "empty", "available", "open", "unoccupied"]) else "Occupied"
        )
    else:
        clean["status"] = clean["tenant"].apply(
            lambda x: "Vacant" if x in ["Vacant", "Unknown", "nan", ""] else "Occupied"
        )

    for date_field in ["lease_start", "lease_end"]:
        if date_field in mapping:
            clean[date_field] = pd.to_datetime(df[mapping[date_field]], errors="coerce", dayfirst=False)
        else:
            clean[date_field] = pd.NaT

    if "unit_type" in mapping:
        clean["unit_type"] = df[mapping["unit_type"]].astype(str).str.strip()
        clean["unit_type"] = clean["unit_type"].replace(["nan", "None", ""], "Standard")
    else:
        clean["unit_type"] = "Standard"

    if "property" in mapping:
        clean["property"] = df[mapping["property"]].astype(str).str.strip()
        clean["property"] = clean["property"].replace(["nan", "None", ""], "Portfolio")
    else:
        clean["property"] = "Portfolio"

    clean["annual_rent"] = clean["monthly_rent"] * 12
    # Rent per LOA (for marinas) or per SqFt (traditional RE)
    if clean["loa"].notna().any() and (clean["loa"] > 0).any():
        clean["rent_per_loa"] = np.where(clean["loa"] > 0, clean["monthly_rent"] / clean["loa"], np.nan)
    else:
        clean["rent_per_loa"] = np.nan
    clean["rent_per_sqft"] = np.where(clean["sqft"] > 0, clean["annual_rent"] / clean["sqft"], np.nan)

    if clean["market_rent"].notna().any():
        clean["loss_to_lease"] = np.where(
            (clean["market_rent"] > 0) & (clean["status"] == "Occupied"),
            clean["market_rent"] - clean["monthly_rent"], 0
        )
    else:
        clean["loss_to_lease"] = 0.0

    today = pd.Timestamp.today().normalize()
    clean["months_remaining"] = np.where(
        clean["lease_end"].notna(),
        ((clean["lease_end"] - today).dt.days / 30.44).clip(lower=0),
        np.nan,
    )

    def exp_bucket(end_date):
        if pd.isna(end_date):
            return "No End Date"
        months = (end_date - today).days / 30.44
        if months < 0:
            return "Expired"
        elif months <= 12:
            return "0-12 Mo"
        elif months <= 24:
            return "12-24 Mo"
        elif months <= 36:
            return "24-36 Mo"
        else:
            return "36+ Mo"

    clean["exp_bucket"] = clean["lease_end"].apply(exp_bucket)
    return clean


# ════════════════════════════════════════════
# PDF PARSING ENGINE
# ════════════════════════════════════════════

def parse_marina_rate_pdf(file_bytes):
    """Parse table-based marina rate sheet PDFs (like Pier-43-RR.pdf)."""
    pdf = pdfplumber.open(io.BytesIO(file_bytes))
    all_rows = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            all_rows.extend(table)
    pdf.close()

    records = []
    current_section = "Dry Storage"
    section_headers = {
        "awning": "Awning Storage", "wet slip": "Wet Slips",
        "mini storage": "Mini Storage", "dry storage": "Dry Storage",
    }
    skip_keywords = [
        "total", "monthly earning", "potential", "storage complete",
        "local competitor", "dockside", "captain", "we are the only",
        "future revenue", "new dry storage", "in progress", "wet slip construction",
        "pier 43 tenant", "if all tenant", "storage type", "tentant",
    ]

    for row in all_rows:
        if not row or all(not str(c or "").strip() for c in row):
            continue
        col0 = str(row[0] or "").strip()
        col0_lower = col0.lower()
        is_section = False
        for key, section_name in section_headers.items():
            if key in col0_lower:
                current_section = section_name
                is_section = True
                break
        if is_section:
            continue
        full_row_text = " ".join(str(c or "") for c in row).lower()
        if any(kw in full_row_text for kw in skip_keywords):
            continue
        if not col0 or not re.match(r"^[A-Za-z]?\d", col0):
            continue

        col1 = str(row[1] or "").strip()
        if col1.upper() == "EMPTY" or not col1:
            records.append({
                "unit": col0, "unit_type": current_section, "monthly_rent": 0,
                "market_rent": np.nan, "status": "Vacant", "property": "Marina",
                "tenant": "Vacant",
            })
            continue

        rent_str = col1.replace("$", "").replace(",", "").strip()
        rent_match = re.match(r"([\d.]+)\s*(?:/\s*\d+)?", rent_str)
        if rent_match:
            monthly_rent = float(rent_match.group(1))
        else:
            continue

        market_rent = np.nan
        if len(row) > 3 and row[3]:
            market_str = str(row[3]).replace("$", "").replace(",", "").strip()
            try:
                market_rent = float(market_str)
            except (ValueError, TypeError):
                pass

        records.append({
            "unit": col0, "unit_type": current_section,
            "monthly_rent": monthly_rent, "market_rent": market_rent,
            "status": "Occupied", "property": "Marina", "tenant": f"Tenant-{col0}",
        })

    return pd.DataFrame(records) if records else None


def parse_tenant_detail_pdf(file_bytes):
    """Parse tenant detail PDFs with PII (like Pier-43-Tenants)."""
    pdf = pdfplumber.open(io.BytesIO(file_bytes))
    all_rows = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            all_rows.extend(table)
    pdf.close()

    records = []
    category_keywords = ["pontoon", "wet slip", "dry", "winter", "rental boat",
                         "inventory", "trailer", "mini", "awning"]
    current_category = "Standard"

    for row in all_rows:
        if not row or all(not str(c or "").strip() for c in row):
            continue
        col0 = str(row[0] or "").strip()
        col0_lower = col0.lower()

        # Detect category labels
        if any(kw in col0_lower for kw in category_keywords) and len(col0) < 30:
            current_category = col0.title()
            continue

        # Skip header rows
        if "first name" in col0_lower or "last name" in col0_lower:
            continue

        # Need at least first name and slip#
        if len(row) < 3:
            continue

        first_name = str(row[0] or "").strip()
        last_name = str(row[1] or "").strip() if len(row) > 1 else ""
        slip_num = str(row[2] or "").strip() if len(row) > 2 else ""
        payment = str(row[3] or "").strip() if len(row) > 3 else ""

        if not first_name or not slip_num:
            continue
        # Skip if looks like a non-tenant row
        if first_name.lower() in ["total", "count", "sum", ""]:
            continue

        tenant_name = f"{first_name} {last_name}".strip()
        rent_val = 0.0
        if payment:
            rent_str = payment.replace("$", "").replace(",", "").strip()
            try:
                rent_val = float(rent_str)
            except (ValueError, TypeError):
                pass

        records.append({
            "unit": slip_num, "tenant": tenant_name,
            "unit_type": current_category, "monthly_rent": rent_val,
            "status": "Occupied" if tenant_name else "Vacant",
            "property": "Marina",
        })

    return pd.DataFrame(records) if records else None


def parse_pdf_generic(file_bytes):
    """Try multiple PDF parsers, return best result."""
    # Try rate sheet first
    df1 = parse_marina_rate_pdf(file_bytes)
    if df1 is not None and len(df1) > 5:
        return df1

    # Try tenant detail
    df2 = parse_tenant_detail_pdf(file_bytes)
    if df2 is not None and len(df2) > 3:
        return df2

    # Fallback: extract all text tables generically
    pdf = pdfplumber.open(io.BytesIO(file_bytes))
    all_rows = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            all_rows.extend(table)
    pdf.close()

    if not all_rows:
        return None

    # Try to build a DataFrame from the first table
    headers = [str(h or f"col_{i}").strip() for i, h in enumerate(all_rows[0])]
    data = all_rows[1:]
    df = pd.DataFrame(data, columns=headers)
    df = df.dropna(how="all").reset_index(drop=True)
    return df if len(df) > 0 else None


# ════════════════════════════════════════════
# EXCEL/CSV PARSING WITH HEADER DETECTION
# ════════════════════════════════════════════

def parse_excel_smart(file_bytes, filename):
    """Parse Excel/CSV with smart header detection (handles offset headers)."""
    if filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(file_bytes))
    else:
        # Try reading first to detect header row
        df_raw = pd.read_excel(io.BytesIO(file_bytes), header=None, nrows=10)
        # Find the most likely header row (row with most non-null string values)
        best_row = 0
        best_score = 0
        for i in range(min(5, len(df_raw))):
            row_vals = df_raw.iloc[i]
            score = sum(1 for v in row_vals if isinstance(v, str) and len(str(v).strip()) > 1)
            if score > best_score:
                best_score = score
                best_row = i

        df = pd.read_excel(io.BytesIO(file_bytes), header=best_row)

    # Drop fully empty rows
    df = df.dropna(how="all").reset_index(drop=True)

    # Drop summary rows at bottom (rows where unit/name is NaN but some numeric cols exist)
    # Heuristic: if last N rows have many NaN values, drop them
    if len(df) > 10:
        tail = df.tail(5)
        null_pcts = tail.isnull().mean(axis=1)
        cutoff = len(df) - len(tail[null_pcts > 0.5])
        df = df.iloc[:cutoff].reset_index(drop=True)

    return df


# ════════════════════════════════════════════
# KPI COMPUTATION
# ════════════════════════════════════════════

def compute_kpis(df):
    total_units = len(df)
    occupied = df[df["status"] == "Occupied"]
    vacant = df[df["status"] == "Vacant"]
    occupied_count = len(occupied)
    vacant_count = len(vacant)
    occupancy_pct = (occupied_count / total_units * 100) if total_units > 0 else 0

    if df["market_rent"].notna().any():
        gpr_monthly = df["market_rent"].fillna(df["monthly_rent"]).sum()
    else:
        gpr_monthly = df["monthly_rent"].sum()

    egr_monthly = occupied["monthly_rent"].sum()
    economic_occ = (egr_monthly / gpr_monthly * 100) if gpr_monthly > 0 else 0
    avg_rent_unit = occupied["monthly_rent"].mean() if occupied_count > 0 else 0

    # Avg rent per LOA (marina metric)
    occ_with_loa = occupied[occupied["loa"] > 0] if "loa" in occupied.columns else pd.DataFrame()
    avg_rent_loa = None
    if len(occ_with_loa) > 0:
        avg_rent_loa = round(float(occ_with_loa["monthly_rent"].sum() / occ_with_loa["loa"].sum()), 2)

    avg_loa = None
    if len(occ_with_loa) > 0:
        avg_loa = round(float(occ_with_loa["loa"].mean()), 1)

    occ_with_sqft = occupied[occupied["sqft"] > 0] if "sqft" in occupied.columns else pd.DataFrame()
    avg_rent_sqft = None
    if len(occ_with_sqft) > 0:
        avg_rent_sqft = occ_with_sqft["annual_rent"].sum() / occ_with_sqft["sqft"].sum()

    wale = None
    occ_with_end = occupied[occupied["months_remaining"].notna() & (occupied["monthly_rent"] > 0)]
    if len(occ_with_end) > 0:
        wale = float(np.average(occ_with_end["months_remaining"], weights=occ_with_end["monthly_rent"]))

    today = pd.Timestamp.today().normalize()
    has_end = occupied[occupied["lease_end"].notna()]
    exp_12 = int(len(has_end[has_end["lease_end"] <= today + timedelta(days=365)]))
    exp_24 = int(len(has_end[has_end["lease_end"] <= today + timedelta(days=730)]))
    exp_36 = int(len(has_end[has_end["lease_end"] <= today + timedelta(days=1095)]))

    ltl_pct = None
    if df["market_rent"].notna().any():
        total_market = occupied[occupied["market_rent"] > 0]["market_rent"].sum()
        total_actual = occupied[occupied["market_rent"] > 0]["monthly_rent"].sum()
        ltl_pct = float((total_market - total_actual) / total_market * 100) if total_market > 0 else 0

    total_monthly = float(occupied["monthly_rent"].sum())
    total_annual = total_monthly * 12

    return {
        "total_units": int(total_units),
        "occupied": int(occupied_count),
        "vacant": int(vacant_count),
        "occupancy_pct": round(float(occupancy_pct), 1),
        "gpr_monthly": round(float(gpr_monthly), 0),
        "gpr_annual": round(float(gpr_monthly * 12), 0),
        "egr_monthly": round(float(egr_monthly), 0),
        "economic_occ": round(float(economic_occ), 1),
        "avg_rent_unit": round(float(avg_rent_unit), 0),
        "avg_rent_sqft": round(float(avg_rent_sqft), 2) if avg_rent_sqft else None,
        "avg_rent_loa": avg_rent_loa,
        "avg_loa": avg_loa,
        "wale_months": round(wale, 1) if wale else None,
        "exp_12": exp_12,
        "exp_24": exp_24,
        "exp_36": exp_36,
        "ltl_pct": round(ltl_pct, 1) if ltl_pct is not None else None,
        "total_monthly": round(total_monthly, 0),
        "total_annual": round(total_annual, 0),
    }


# ════════════════════════════════════════════
# AUTO-CLEANUP ENGINE
# ════════════════════════════════════════════

def auto_cleanup(df):
    """Run automatic data cleanup steps. Returns (cleaned_df, cleanup_log)."""
    log = []
    original_len = len(df)

    # 1. Remove exact duplicate rows
    before = len(df)
    df = df.drop_duplicates()
    removed_dupes = before - len(df)
    if removed_dupes > 0:
        log.append({"action": "Removed duplicates", "count": removed_dupes, "severity": "info"})

    # 2. Trim whitespace in all string columns
    trimmed = 0
    for col in df.select_dtypes(include=["object"]).columns:
        old_vals = df[col].copy()
        df[col] = df[col].astype(str).str.strip()
        trimmed += (old_vals != df[col]).sum()
    if trimmed > 0:
        log.append({"action": "Trimmed whitespace", "count": int(trimmed), "severity": "info"})

    # 3. Normalize tenant names (title case)
    if "tenant" in df.columns:
        before_vals = df["tenant"].copy()
        df["tenant"] = df["tenant"].str.title()
        normalized = int((before_vals != df["tenant"]).sum())
        if normalized > 0:
            log.append({"action": "Normalized tenant names to title case", "count": normalized, "severity": "info"})

    # 4. Fix negative rents
    if "monthly_rent" in df.columns:
        neg_rents = (df["monthly_rent"] < 0).sum()
        if neg_rents > 0:
            df["monthly_rent"] = df["monthly_rent"].abs()
            log.append({"action": "Fixed negative rent values", "count": int(neg_rents), "severity": "warning"})

    # 5. Flag zero-rent occupied units
    if "monthly_rent" in df.columns and "status" in df.columns:
        zero_occ = ((df["monthly_rent"] == 0) & (df["status"] == "Occupied")).sum()
        if zero_occ > 0:
            log.append({"action": "Occupied units with $0 rent (review needed)", "count": int(zero_occ), "severity": "warning"})

    # 6. Flag missing unit IDs
    if "unit" in df.columns:
        missing_units = df["unit"].isin(["nan", "None", ""]).sum()
        if missing_units > 0:
            log.append({"action": "Missing unit identifiers", "count": int(missing_units), "severity": "warning"})

    # 7. Detect potential duplicates by unit number
    if "unit" in df.columns:
        dup_units = df["unit"].duplicated(keep=False).sum()
        if dup_units > 0:
            log.append({"action": "Possible duplicate unit numbers", "count": int(dup_units // 2), "severity": "warning"})

    return df.reset_index(drop=True), log


# ════════════════════════════════════════════
# CLAUDE AI CLEANUP
# ════════════════════════════════════════════

async def claude_analyze(df, column_mapping):
    """Use Claude to analyze data quality and suggest fixes."""
    if not HAS_CLAUDE:
        return {"issues": [], "summary": "Claude AI unavailable. Using rule-based analysis only."}

    # Prepare data sample for Claude
    sample = df.head(20).to_csv(index=False)
    stats = {
        "total_rows": len(df),
        "columns": list(df.columns),
        "mapping": column_mapping,
        "null_counts": df.isnull().sum().to_dict(),
        "unique_statuses": df["status"].unique().tolist() if "status" in df.columns else [],
        "unique_types": df["unit_type"].unique().tolist() if "unit_type" in df.columns else [],
    }

    prompt = f"""You are a data quality analyst reviewing a marina/real estate rent roll dataset.

DATA STATISTICS:
{json.dumps(stats, default=str, indent=2)}

SAMPLE DATA (first 20 rows):
{sample}

Analyze this data for quality issues. For each issue found, return a JSON object with:
- "issue": short description
- "severity": "error" or "warning" or "info"
- "affected_rows": approximate count
- "suggestion": what to do about it

Also provide a brief 2-3 sentence summary of overall data quality.

Return ONLY valid JSON in this format:
{{"issues": [...], "summary": "..."}}"""

    try:
        message = claude_client.messages.create(
            model="claude_sonnet_4_5",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            return json.loads(json_match.group())
        return {"issues": [], "summary": response_text[:500]}
    except Exception as e:
        return {"issues": [], "summary": f"AI analysis error: {str(e)[:200]}"}


# ════════════════════════════════════════════
# INSIGHT ENGINE
# ════════════════════════════════════════════

def generate_insights(df, kpis):
    insights = []
    occupied = df[df["status"] == "Occupied"]
    occ = kpis["occupancy_pct"]

    if occ >= 95:
        insights.append({
            "title": "Occupancy Strength",
            "text": f"Physical occupancy at {occ:.1f}% indicates strong demand and limited near-term lease-up risk. Evaluate whether current rents have room to move to market.",
            "type": "success"
        })
    elif occ >= 85:
        insights.append({
            "title": "Occupancy Assessment",
            "text": f"Physical occupancy is {occ:.1f}%, within the stabilized band. Focus on converting the {kpis['vacant']} vacant unit(s) to push above 90%.",
            "type": "info"
        })
    else:
        insights.append({
            "title": "Occupancy Concern",
            "text": f"Physical occupancy at {occ:.1f}% is below stabilized levels. The {kpis['vacant']} vacant unit(s) represent a {100-occ:.1f}% vacancy drag on revenue.",
            "type": "warning"
        })

    if kpis["economic_occ"] < kpis["occupancy_pct"] - 3:
        gap = kpis["occupancy_pct"] - kpis["economic_occ"]
        insights.append({
            "title": "Economic Occupancy Gap",
            "text": f"Economic occupancy ({kpis['economic_occ']:.1f}%) trails physical ({occ:.1f}%) by {gap:.1f} pts, signaling concessions or below-market leases are compressing effective revenue.",
            "type": "warning"
        })

    if kpis["ltl_pct"] is not None and kpis["ltl_pct"] > 5:
        ltl_monthly = float(occupied["loss_to_lease"].sum())
        insights.append({
            "title": "Loss-to-Lease Upside",
            "text": f"At {kpis['ltl_pct']:.1f}%, there is ~${ltl_monthly:,.0f}/mo (${ltl_monthly*12:,.0f}/yr) in mark-to-market upside. Prioritize units furthest below market on next renewal.",
            "type": "info"
        })

    if kpis["exp_12"] > 0:
        pct_12 = kpis["exp_12"] / max(kpis["occupied"], 1) * 100
        insights.append({
            "title": "Near-Term Rollover",
            "text": f"{kpis['exp_12']} lease(s) ({pct_12:.0f}% of occupied) expire within 12 months. Model renewal probability and downtime assumptions carefully.",
            "type": "warning" if pct_12 > 25 else "info"
        })

    if len(occupied) > 0:
        by_tenant = occupied.groupby("tenant")["monthly_rent"].sum().sort_values(ascending=False)
        total_rev = by_tenant.sum()
        if total_rev > 0:
            top_pct = float(by_tenant.iloc[0] / total_rev * 100)
            if top_pct > 25:
                insights.append({
                    "title": "Concentration Risk",
                    "text": f"Top tenant (\"{by_tenant.index[0]}\") accounts for {top_pct:.1f}% of total revenue. Single-tenant exposure above 25% warrants credit analysis.",
                    "type": "warning"
                })

    if kpis["wale_months"] is not None:
        wale_yrs = kpis["wale_months"] / 12
        if wale_yrs < 2:
            insights.append({
                "title": "Short WALE",
                "text": f"WALE is {wale_yrs:.1f} years — creates re-leasing risk but also opportunity to mark rents to market quickly.",
                "type": "warning"
            })

    return insights


# ════════════════════════════════════════════
# CHART DATA ENDPOINTS
# ════════════════════════════════════════════

def get_chart_data(df):
    """Compute all chart data for frontend rendering."""
    charts = {}

    # Occupancy donut
    status_counts = df["status"].value_counts().to_dict()
    charts["occupancy"] = {"labels": list(status_counts.keys()), "values": list(int(v) for v in status_counts.values())}

    # Rent distribution histogram
    occupied = df[(df["status"] == "Occupied") & (df["monthly_rent"] > 0)]
    if len(occupied) > 0:
        rents = occupied["monthly_rent"].dropna().tolist()
        charts["rent_distribution"] = {"values": [round(r, 2) for r in rents]}
    else:
        charts["rent_distribution"] = {"values": []}

    # Lease expiration — monthly for next 12 months (annual contracts)
    occ = df[df["status"] == "Occupied"]
    today = pd.Timestamp.today().normalize()
    has_end = occ[occ["lease_end"].notna()].copy()
    no_end = occ[occ["lease_end"].isna()]

    month_labels = []
    month_units = []
    month_rent = []
    for i in range(12):
        mo_start = (today + pd.DateOffset(months=i)).replace(day=1)
        mo_end = (today + pd.DateOffset(months=i + 1)).replace(day=1) - pd.Timedelta(days=1)
        label = mo_start.strftime("%b %Y")
        in_month = has_end[(has_end["lease_end"] >= mo_start) & (has_end["lease_end"] <= mo_end)]
        month_labels.append(label)
        month_units.append(int(len(in_month)))
        month_rent.append(round(float(in_month["monthly_rent"].sum()), 0))

    # Add expired and no-end-date buckets
    expired = has_end[has_end["lease_end"] < today]
    beyond_12 = has_end[has_end["lease_end"] > today + pd.DateOffset(months=12)]

    charts["lease_expiration"] = {
        "labels": ["Expired"] + month_labels + ["12+ Mo", "No End Date"],
        "units": [int(len(expired))] + month_units + [int(len(beyond_12)), int(len(no_end))],
        "rent": [
            round(float(expired["monthly_rent"].sum()), 0)
        ] + month_rent + [
            round(float(beyond_12["monthly_rent"].sum()), 0),
            round(float(no_end["monthly_rent"].sum()), 0),
        ],
    }

    # Revenue by type
    occ_by_type = occ.groupby("unit_type")["monthly_rent"].sum().sort_values(ascending=True)
    charts["revenue_by_type"] = {
        "labels": occ_by_type.index.tolist(),
        "values": [round(float(v), 0) for v in occ_by_type.values],
    }

    # Rent vs size scatter
    scatter_df = occ[(occ["sqft"] > 0) & (occ["monthly_rent"] > 0)]
    if len(scatter_df) > 0:
        charts["rent_vs_size"] = {
            "x": [round(float(v), 0) for v in scatter_df["sqft"].values],
            "y": [round(float(v), 2) for v in scatter_df["monthly_rent"].values],
            "labels": scatter_df["unit"].tolist(),
            "types": scatter_df["unit_type"].tolist(),
        }
    else:
        charts["rent_vs_size"] = None

    # Tenant concentration
    if len(occ) > 0:
        by_tenant = occ.groupby("tenant").agg(
            units=("unit", "count"),
            monthly_rent=("monthly_rent", "sum"),
        ).sort_values("monthly_rent", ascending=False)
        total_rev = by_tenant["monthly_rent"].sum()
        by_tenant["pct"] = (by_tenant["monthly_rent"] / total_rev * 100).round(1)
        top10 = by_tenant.head(10).reset_index()
        charts["concentration"] = {
            "tenants": top10["tenant"].tolist(),
            "rent": [round(float(v), 0) for v in top10["monthly_rent"].values],
            "pct": [float(v) for v in top10["pct"].values],
            "units": [int(v) for v in top10["units"].values],
        }
    else:
        charts["concentration"] = None

    # Seasonal data
    has_dates = occ[occ["lease_start"].notna() & occ["lease_end"].notna()].copy()
    if len(has_dates) >= 3:
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        def active_months(row):
            start, end = row["lease_start"], row["lease_end"]
            if pd.isna(start) or pd.isna(end):
                return set(range(1, 13))
            months = set()
            current = start.replace(day=1)
            end_ceil = end.replace(day=1)
            while current <= end_ceil:
                months.add(current.month)
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)
            return months

        has_dates = has_dates.copy()
        has_dates["active_months"] = has_dates.apply(active_months, axis=1)
        monthly = []
        for mo in range(1, 13):
            active = has_dates[has_dates["active_months"].apply(lambda s: mo in s)]
            monthly.append({
                "month": month_names[mo - 1],
                "units": int(len(active)),
                "revenue": round(float(active["monthly_rent"].sum()), 0),
            })
        peak_rev = max(m["revenue"] for m in monthly) if monthly else 1
        for m in monthly:
            m["pct_of_peak"] = round(m["revenue"] / peak_rev * 100, 0) if peak_rev > 0 else 0
            m["occupancy_pct"] = round(m["units"] / len(has_dates) * 100, 1) if len(has_dates) > 0 else 0

        charts["seasonal"] = {"months": monthly}

        # Start/end clustering
        start_counts = has_dates["lease_start"].dt.month.value_counts().sort_index()
        end_counts = has_dates["lease_end"].dt.month.value_counts().sort_index()
        charts["lease_clustering"] = {
            "months": month_names,
            "starts": [int(start_counts.get(i, 0)) for i in range(1, 13)],
            "ends": [int(end_counts.get(i, 0)) for i in range(1, 13)],
        }
    else:
        charts["seasonal"] = None
        charts["lease_clustering"] = None

    return charts


# ════════════════════════════════════════════
# TENANT DEMOGRAPHICS ANALYSIS
# ════════════════════════════════════════════

def compute_demographics(df):
    """Compute tenant demographic analysis from address/zip/home value data."""
    result = {"has_data": False, "home_value": None, "geographic": None, "boat_info": None}
    occupied = df[df["status"] == "Occupied"].copy()
    if len(occupied) == 0:
        return result

    # ── Home Value Analysis ──
    has_hv = occupied[occupied["home_value"].notna() & (occupied["home_value"] > 0)]
    if len(has_hv) >= 3:
        result["has_data"] = True

        def home_tier(v):
            if v >= 500000:
                return "Premium"
            elif v >= 350000:
                return "Strong"
            elif v >= 200000:
                return "Moderate"
            else:
                return "Entry"

        tier_ranges = {
            "Premium": "$500K+",
            "Strong": "$350K\u2013$500K",
            "Moderate": "$200K\u2013$350K",
            "Entry": "Under $200K",
        }

        has_hv = has_hv.copy()
        has_hv["value_tier"] = has_hv["home_value"].apply(home_tier)
        tier_order = ["Premium", "Strong", "Moderate", "Entry"]
        tier_data = []
        for tier in tier_order:
            group = has_hv[has_hv["value_tier"] == tier]
            if len(group) > 0:
                tier_data.append({
                    "tier": tier,
                    "range": tier_ranges[tier],
                    "count": int(len(group)),
                    "pct": round(float(len(group) / len(has_hv) * 100), 1),
                    "avg_value": round(float(group["home_value"].mean()), 0),
                })

        result["home_value"] = {
            "total_tenants": int(len(occupied)),
            "values_found": int(len(has_hv)),
            "match_rate": round(float(len(has_hv) / len(occupied) * 100), 1),
            "median_value": round(float(has_hv["home_value"].median()), 0),
            "avg_value": round(float(has_hv["home_value"].mean()), 0),
            "tiers": tier_data,
            # Rent-to-value ratio (bps)
            "avg_rent_value_bps": round(float(
                has_hv["annual_rent"].sum() / has_hv["home_value"].sum() * 10000
            ), 1) if has_hv["home_value"].sum() > 0 else None,
        }

    # ── Geographic / ZIP Analysis ──
    has_zip = occupied[occupied["zip_code"].astype(str).str.len() == 5].copy()
    if len(has_zip) >= 3:
        result["has_data"] = True
        by_zip = has_zip.groupby("zip_code").agg(
            tenants=("unit", "count"),
            total_rent=("monthly_rent", "sum"),
        ).sort_values("tenants", ascending=False).reset_index()
        by_zip["pct"] = (by_zip["tenants"] / by_zip["tenants"].sum() * 100).round(1)
        by_zip["avg_rent"] = (by_zip["total_rent"] / by_zip["tenants"]).round(0)

        # If home values available, add avg home value per zip
        if len(has_hv) >= 3:
            zip_hv = has_hv.groupby("zip_code")["home_value"].mean().round(0).to_dict()
            by_zip["avg_home_value"] = by_zip["zip_code"].map(zip_hv)
        else:
            by_zip["avg_home_value"] = np.nan

        top_zips = by_zip.head(15)
        result["geographic"] = {
            "total_zips": int(by_zip["zip_code"].nunique()),
            "top_zip": top_zips.iloc[0]["zip_code"] if len(top_zips) > 0 else None,
            "top_zip_pct": float(top_zips.iloc[0]["pct"]) if len(top_zips) > 0 else 0,
            "zips": [{
                "zip": row["zip_code"],
                "tenants": int(row["tenants"]),
                "pct": float(row["pct"]),
                "avg_rent": float(row["avg_rent"]),
                "avg_home_value": float(row["avg_home_value"]) if pd.notna(row["avg_home_value"]) else None,
            } for _, row in top_zips.iterrows()],
        }

    # ── Boat Info Analysis ──
    boat_cols = ["boat_make", "boat_model", "boat_year", "loa"]
    has_boat = occupied[
        occupied[boat_cols].apply(lambda r: any(
            str(v).strip() not in ["", "nan", "None"] and pd.notna(v) and v != 0
            for v in r
        ), axis=1)
    ].copy() if all(c in occupied.columns for c in boat_cols) else pd.DataFrame()

    if len(has_boat) >= 3:
        result["has_data"] = True
        boat_stats = {
            "total_with_info": int(len(has_boat)),
            "pct_fleet": round(float(len(has_boat) / len(occupied) * 100), 1),
        }

        # LOA distribution
        with_loa = has_boat[has_boat["loa"].notna() & (has_boat["loa"] > 0)]
        if len(with_loa) >= 3:
            boat_stats["avg_loa"] = round(float(with_loa["loa"].mean()), 1)
            boat_stats["median_loa"] = round(float(with_loa["loa"].median()), 1)
            boat_stats["min_loa"] = round(float(with_loa["loa"].min()), 0)
            boat_stats["max_loa"] = round(float(with_loa["loa"].max()), 0)
            # LOA size buckets
            def loa_bucket(v):
                if v < 20:
                    return "Under 20\'"
                elif v < 25:
                    return "20\'-24\'"
                elif v < 30:
                    return "25\'-29\'"
                elif v < 35:
                    return "30\'-34\'"
                else:
                    return "35\'+"
            with_loa = with_loa.copy()
            with_loa["loa_bucket"] = with_loa["loa"].apply(loa_bucket)
            bucket_order = ["Under 20\'", "20\'-24\'", "25\'-29\'", "30\'-34\'", "35\'+"]
            loa_dist = with_loa.groupby("loa_bucket").agg(
                count=("unit", "count"),
                avg_rent=("monthly_rent", "mean"),
            ).reindex(bucket_order).fillna(0)
            boat_stats["loa_distribution"] = [{
                "bucket": b,
                "count": int(loa_dist.loc[b, "count"]) if b in loa_dist.index else 0,
                "avg_rent": round(float(loa_dist.loc[b, "avg_rent"]), 0) if b in loa_dist.index else 0,
            } for b in bucket_order]

        # Top makes
        with_make = has_boat[has_boat["boat_make"].str.len() > 0]
        if len(with_make) >= 3:
            top_makes = with_make["boat_make"].value_counts().head(10)
            boat_stats["top_makes"] = [{
                "make": make, "count": int(count),
                "pct": round(float(count / len(with_make) * 100), 1),
            } for make, count in top_makes.items()]

        # Avg year
        with_year = has_boat[has_boat["boat_year"].str.match(r"^\d{4}$", na=False)]
        if len(with_year) >= 3:
            years = with_year["boat_year"].astype(int)
            boat_stats["avg_year"] = int(years.mean())
            boat_stats["newest_year"] = int(years.max())
            boat_stats["oldest_year"] = int(years.min())

        result["boat_info"] = boat_stats

    return result


# ════════════════════════════════════════════
# API ENDPOINTS
# ════════════════════════════════════════════

@app.post("/api/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    """Upload and parse a rent roll file."""
    visitor = get_visitor(request)
    file_bytes = await file.read()
    filename = file.filename.lower()

    try:
        if filename.endswith(".pdf"):
            raw_df = parse_pdf_generic(file_bytes)
            if raw_df is None or len(raw_df) == 0:
                raise HTTPException(status_code=400, detail="Could not extract data from PDF. Try Excel or CSV format.")
            # If we got structured data from PDF parser, check if it needs column mapping
            if "monthly_rent" in raw_df.columns and "unit" in raw_df.columns:
                # Already parsed into standard format
                mapping = {col: col for col in raw_df.columns if col in COLUMN_MAP or col in ["tenant", "unit", "unit_type", "monthly_rent", "market_rent", "status", "property"]}
                # Fill missing standard fields
                for col, default in [
                    ("sqft", np.nan), ("loa", np.nan),
                    ("lease_start", pd.NaT), ("lease_end", pd.NaT),
                    ("market_rent", np.nan), ("status", "Occupied"),
                    ("unit_type", "Unit"), ("property", "Property"),
                    ("tenant", ""), ("rent_per_sqft", np.nan),
                    ("rent_per_loa", np.nan), ("months_remaining", np.nan),
                    ("address", ""), ("zip_code", ""),
                    ("home_value", np.nan),
                    ("boat_make", ""), ("boat_model", ""), ("boat_year", ""),
                ]:
                    if col not in raw_df.columns:
                        raw_df[col] = default
                if "annual_rent" not in raw_df.columns:
                    raw_df["annual_rent"] = raw_df["monthly_rent"] * 12
                if "loss_to_lease" not in raw_df.columns:
                    if "market_rent" in raw_df.columns and raw_df["market_rent"].notna().any():
                        raw_df["loss_to_lease"] = np.where(
                            (raw_df["market_rent"] > 0) & (raw_df["status"] == "Occupied"),
                            raw_df["market_rent"] - raw_df["monthly_rent"], 0
                        )
                    else:
                        raw_df["loss_to_lease"] = 0.0
                if "exp_bucket" not in raw_df.columns:
                    raw_df["exp_bucket"] = "No End Date"
                clean_df = raw_df
            else:
                mapping = map_columns(raw_df)
                if "monthly_rent" not in mapping and "annual_rent" not in mapping:
                    raise HTTPException(status_code=400, detail="Could not detect rent column in PDF data.")
                clean_df = clean_dataframe(raw_df, mapping)
        else:
            raw_df = parse_excel_smart(file_bytes, filename)
            mapping = map_columns(raw_df)
            if "monthly_rent" not in mapping and "annual_rent" not in mapping:
                return JSONResponse(status_code=400, content={
                    "detail": "Could not detect a rent column.",
                    "columns": list(raw_df.columns),
                })
            clean_df = clean_dataframe(raw_df, mapping)

        # Auto cleanup
        clean_df, cleanup_log = auto_cleanup(clean_df)

        # Store in session
        sessions[visitor] = {
            "raw_df": raw_df,
            "clean_df": clean_df,
            "mapping": mapping,
            "cleanup_log": cleanup_log,
            "filename": file.filename,
            "uploaded_at": datetime.now().isoformat(),
        }

        # Compute initial data
        kpis = compute_kpis(clean_df)
        charts = get_chart_data(clean_df)
        insights = generate_insights(clean_df, kpis)
        demographics = compute_demographics(clean_df)

        # Build table data (JSON-safe)
        table_df = clean_df.copy()
        for dc in ["lease_start", "lease_end"]:
            if dc in table_df.columns:
                table_df[dc] = table_df[dc].dt.strftime("%Y-%m-%d").fillna("")
        table_df = table_df.fillna("")
        # Convert any remaining NaN/inf
        table_df = table_df.replace([np.inf, -np.inf], 0)

        return {
            "success": True,
            "filename": file.filename,
            "rows": len(clean_df),
            "columns": list(clean_df.columns),
            "mapping": {k: str(v) for k, v in mapping.items()},
            "cleanup_log": cleanup_log,
            "kpis": kpis,
            "charts": charts,
            "insights": insights,
            "demographics": demographics,
            "table": json.loads(table_df.to_json(orient="records")),
            "properties": sorted(clean_df["property"].unique().tolist()),
            "unit_types": sorted(clean_df["unit_type"].unique().tolist()),
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)[:300]}")


@app.post("/api/ai-analyze")
async def ai_analyze(request: Request):
    """Run Claude AI analysis on the uploaded data."""
    visitor = get_visitor(request)
    session = sessions.get(visitor)
    if not session:
        raise HTTPException(status_code=400, detail="No data uploaded. Please upload a file first.")

    result = await claude_analyze(session["clean_df"], session["mapping"])
    return result


@app.post("/api/filter")
async def filter_data(request: Request):
    """Re-compute KPIs and charts with filters applied."""
    visitor = get_visitor(request)
    session = sessions.get(visitor)
    if not session:
        raise HTTPException(status_code=400, detail="No data uploaded.")

    body = await request.json()
    df = session["clean_df"].copy()

    if body.get("properties"):
        df = df[df["property"].isin(body["properties"])]
    if body.get("unit_types"):
        df = df[df["unit_type"].isin(body["unit_types"])]
    if body.get("statuses"):
        df = df[df["status"].isin(body["statuses"])]

    if len(df) == 0:
        return {"error": "No data matches filters"}

    kpis = compute_kpis(df)
    charts = get_chart_data(df)
    insights = generate_insights(df, kpis)

    table_df = df.copy()
    for dc in ["lease_start", "lease_end"]:
        if dc in table_df.columns:
            table_df[dc] = table_df[dc].dt.strftime("%Y-%m-%d").fillna("")
    table_df = table_df.fillna("").replace([np.inf, -np.inf], 0)

    return {
        "kpis": kpis,
        "charts": charts,
        "insights": insights,
        "table": json.loads(table_df.to_json(orient="records")),
        "rows": len(df),
    }


@app.get("/api/export")
async def export_excel(request: Request):
    """Export cleaned data as Excel."""
    visitor = get_visitor(request)
    session = sessions.get(visitor)
    if not session:
        raise HTTPException(status_code=400, detail="No data uploaded.")

    df = session["clean_df"].copy()
    kpis = compute_kpis(df)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Sheet 1: Cleaned rent roll
        export_df = df.copy()
        for dc in ["lease_start", "lease_end"]:
            if dc in export_df.columns:
                export_df[dc] = export_df[dc].dt.strftime("%Y-%m-%d").fillna("")
        col_rename = {
            "property": "Property", "unit": "Unit", "tenant": "Tenant",
            "unit_type": "Type", "status": "Status",
            "monthly_rent": "Monthly Rent", "annual_rent": "Annual Rent",
            "market_rent": "Market Rent", "loss_to_lease": "Loss-to-Lease",
            "loa": "LOA (ft)", "rent_per_loa": "$/LOA",
            "sqft": "SqFt", "rent_per_sqft": "Rent/SqFt",
            "lease_start": "Lease Start", "lease_end": "Lease End",
            "months_remaining": "Mo. Remaining", "exp_bucket": "Exp. Bucket",
            "address": "Address", "zip_code": "ZIP Code",
            "home_value": "Home Value",
            "boat_make": "Boat Make", "boat_model": "Boat Model", "boat_year": "Boat Year",
        }
        export_df = export_df.rename(columns=col_rename)
        export_df.to_excel(writer, sheet_name="Rent Roll", index=False)

        # Format headers
        workbook = writer.book
        header_fmt = workbook.add_format({
            "bold": True, "bg_color": "#1B2A4A", "font_color": "white", "border": 1,
        })
        ws = writer.sheets["Rent Roll"]
        for col_num, col_name in enumerate(export_df.columns):
            ws.write(0, col_num, col_name, header_fmt)
            max_len = max(export_df[col_name].astype(str).str.len().max(), len(col_name)) + 2
            ws.set_column(col_num, col_num, min(max_len, 30))

        # Sheet 2: KPI Summary
        kpi_rows = [
            ("Total Units", kpis["total_units"]),
            ("Occupied Units", kpis["occupied"]),
            ("Vacant Units", kpis["vacant"]),
            ("Physical Occupancy %", f"{kpis['occupancy_pct']:.1f}%"),
            ("Economic Occupancy %", f"{kpis['economic_occ']:.1f}%"),
            ("GPR (Monthly)", f"${kpis['gpr_monthly']:,.0f}"),
            ("GPR (Annual)", f"${kpis['gpr_annual']:,.0f}"),
            ("EGR (Monthly)", f"${kpis['egr_monthly']:,.0f}"),
            ("Avg Rent / Unit", f"${kpis['avg_rent_unit']:,.0f}"),
        ]
        if kpis["avg_rent_sqft"]:
            kpi_rows.append(("Avg Rent / SqFt", f"${kpis['avg_rent_sqft']:.2f}"))
        if kpis["wale_months"]:
            kpi_rows.append(("WALE (Months)", f"{kpis['wale_months']:.1f}"))
        if kpis["ltl_pct"] is not None:
            kpi_rows.append(("Loss-to-Lease %", f"{kpis['ltl_pct']:.1f}%"))
        kpi_df = pd.DataFrame(kpi_rows, columns=["Metric", "Value"])
        kpi_df.to_excel(writer, sheet_name="KPI Summary", index=False)

        ws2 = writer.sheets["KPI Summary"]
        for col_num, col_name in enumerate(kpi_df.columns):
            ws2.write(0, col_num, col_name, header_fmt)
            ws2.set_column(col_num, col_num, 25)

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=rentroll_export_{datetime.now().strftime('%Y%m%d')}.xlsx"}
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "claude": HAS_CLAUDE}


# ── Serve frontend static files from same server ──
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Serve index.html at root
@app.get("/")
def serve_root():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))

# Serve static files (css, js, assets)
app.mount("/", StaticFiles(directory=os.path.dirname(__file__) or "."), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
