
from __future__ import annotations

import io
import math
from typing import List, Optional, Literal, Dict, Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel, Field, conint, confloat
from joblib import dump, load
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # you can restrict later ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ML imports
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score

MODEL_DIR = Path("./models")
MODEL_DIR.mkdir(exist_ok=True)
DISEASE_MODEL_PATH = MODEL_DIR / "disease_model.joblib"
NOSHOW_MODEL_PATH = MODEL_DIR / "noshow_model.joblib"
FEATURES_META_PATH = MODEL_DIR / "features_meta.joblib"


# =========================
# Domain: Data Schemas
# =========================
Sex = Literal["male", "female", "other"]
TimeOfDay = Literal["morning", "afternoon", "evening"]
Weekday = Literal["mon", "tue", "wed", "thu", "fri", "sat"]
Specialty = Literal[
    "general", "cardiology", "endocrinology", "pulmonology",
    "neurology", "dermatology", "orthopedics", "gynecology"
]

class PatientFeatures(BaseModel):
    age: conint(ge=0, le=120) = Field(..., description="Age in years")
    sex: Sex
    chronic_conditions_count: conint(ge=0, le=20) = 0
    previous_no_show_rate: confloat(ge=0, le=1) = 0.0
    days_until_appointment: conint(ge=0, le=365) = 7
    sms_reminders_sent: conint(ge=0, le=10) = 0
    distance_km: confloat(ge=0, le=1000) = 5.0
    time_of_day: TimeOfDay = "morning"
    weekday: Weekday = "mon"
    doctor_specialty: Specialty = "general"
    symptoms_text: str = ""

class PredictRequest(BaseModel):
    patient: PatientFeatures

class PredictResponse(BaseModel):
    disease_risk: float = Field(..., description="Probability of disease/complication (0-1)")
    no_show_probability: float = Field(..., description="Probability of missing appointment (0-1)")
    priority_score: float = Field(..., description="Composite score 0-100")
    recommended_actions: List[str]
    explanation: Dict[str, Any]

class ScheduleRequest(BaseModel):
    patient: PatientFeatures
    candidate_slots: List[Dict[str, str]] = Field(
        ...,
        description="List of slots like [{'weekday':'mon','time_of_day':'morning','date':'2025-09-05'}]"
    )

class ScheduleResponse(BaseModel):
    best_slot: Dict[str, str]
    slot_scores: List[Dict[str, Any]]
    rationale: str

# =========================
# Utilities: Pipeline
# =========================
NUM_COLS = [
    "age",
    "chronic_conditions_count",
    "previous_no_show_rate",
    "days_until_appointment",
    "sms_reminders_sent",
    "distance_km",
]

CAT_COLS = [
    "sex", "time_of_day", "weekday", "doctor_specialty"
]

TEXT_COL = "symptoms_text"

def build_preprocessor():
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUM_COLS),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_COLS),
            ("txt", TfidfVectorizer(min_df=2, ngram_range=(1, 2)), TEXT_COL),
        ]
    )

def build_models():
    pre = build_preprocessor()
    disease_model = Pipeline(
        steps=[
            ("pre", pre),
            ("clf", LogisticRegression(max_iter=200, n_jobs=None))
        ]
    )
    noshow_model = Pipeline(
        steps=[
            ("pre", pre),
            ("clf", GradientBoostingClassifier())
        ]
    )
    return disease_model, noshow_model

def to_dataframe(p: PatientFeatures) -> pd.DataFrame:
    d = {k: [getattr(p, k)] for k in p.model_dump()}
    return pd.DataFrame(d)

def composite_priority(disease_risk: float, no_show_prob: float) -> float:
    """
    Higher is more urgent to act *now*.
    Rationale:
      - High disease risk increases priority.
      - High no-show increases priority *for intervention* (reminders/telemed),
        but for scheduling we may prefer slots that reduce no-show.
    """
    # Weighted combination (tune as needed)
    score = (0.7 * disease_risk + 0.3 * (0.5 + (no_show_prob - 0.5)))  # center no-show around 0.5
    return float(np.clip(score, 0, 1) * 100)

def recommend_actions(disease_risk: float, no_show: float, pf: PatientFeatures) -> List[str]:
    recs = []

    if disease_risk >= 0.7:
        recs.append("Flag for expedited clinician review")
        recs.append("Offer earliest available slot (≤ 48 hours)")
        recs.append("Provide pre-visit triage call")

    if 0.4 <= disease_risk < 0.7:
        recs.append("Offer appointment within 3–7 days")
        recs.append("Share targeted pre-visit checklist")

    if disease_risk < 0.4:
        recs.append("Standard scheduling window (7–14 days)")

    if no_show >= 0.6:
        recs.append("Enable SMS + WhatsApp reminder sequence (T-72h, T-24h, T-2h)")
        recs.append("Suggest telemedicine if travel distance is high")
        if pf.days_until_appointment > 14:
            recs.append("Reduce lead time: offer earlier slot to lower forgetfulness")

    elif 0.3 <= no_show < 0.6:
        recs.append("Send single reminder at T-24h")
        recs.append("Prefer morning slots (higher attendance)")

    else:
        recs.append("Standard reminder at T-24h")
    return recs

def slot_attendance_adjustment(weekday: str, time_of_day: str) -> float:
    """
    Heuristic: morning and mid-week tend to have lower no-show rates.
    You should replace with historical clinic stats when available.
    Returns multiplicative factor to *reduce* predicted no-show.
    """
    factor = 1.0
    if time_of_day == "morning":
        factor *= 0.9
    if weekday in {"tue", "wed", "thu"}:
        factor *= 0.9
    if weekday in {"sat"}:
        factor *= 1.05
    return factor

# =========================
# Training (Synthetic + CSV)
# =========================
def _synthetic_data(n: int = 2000) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "age": rng.integers(18, 85, n),
        "sex": rng.choice(["male", "female", "other"], n, p=[0.48, 0.48, 0.04]),
        "chronic_conditions_count": rng.integers(0, 6, n),
        "previous_no_show_rate": rng.uniform(0, 1, n),
        "days_until_appointment": rng.integers(0, 30, n),
        "sms_reminders_sent": rng.integers(0, 3, n),
        "distance_km": rng.uniform(0, 40, n),
        "time_of_day": rng.choice(["morning", "afternoon", "evening"], n, p=[0.45, 0.35, 0.20]),
        "weekday": rng.choice(["mon", "tue", "wed", "thu", "fri", "sat"], n, p=[.18,.17,.17,.17,.25,.06]),
        "doctor_specialty": rng.choice(
            ["general","cardiology","endocrinology","pulmonology","neurology",
             "dermatology","orthopedics","gynecology"], n),
    })
    # Symptoms text
    symptom_pool = [
        "chest pain and shortness of breath",
        "persistent cough and wheezing",
        "high blood sugar and fatigue",
        "headache dizziness blurred vision",
        "joint pain swelling stiffness",
        "skin rash itching redness",
        "lower abdominal pain nausea",
        "fever sore throat",
        "mild back pain",
        "annual checkup no symptoms"
    ]
    df["symptoms_text"] = rng.choice(symptom_pool, n)

    # latent risk signal (for synthetic labels only)
    risk_signal = (
        (df["age"] > 60).astype(float)*0.25
        + df["chronic_conditions_count"]*0.07
        + df["symptoms_text"].str.contains("chest pain|shortness of breath|high blood sugar", regex=True).astype(float)*0.25
        + (df["doctor_specialty"].isin(["cardiology","endocrinology","pulmonology"])).astype(float)*0.15
    )
    disease_prob = 1 / (1 + np.exp(-(risk_signal - 0.8)))
    df["disease_label"] = (np.random.rand(n) < disease_prob).astype(int)

    # no-show signal: longer lead time, evening, Fri/Sat, distance, past behavior
    noshow_signal = (
        (df["days_until_appointment"]/30)*0.6
        + (df["previous_no_show_rate"])*0.8
        + (df["time_of_day"].eq("evening")).astype(float)*0.2
        + (df["weekday"].isin(["fri","sat"])).astype(float)*0.15
        + (df["distance_km"]/40)*0.2
        - (df["sms_reminders_sent"]*0.15)
    )
    noshow_prob = 1 / (1 + np.exp(-(noshow_signal - 0.8)))
    df["noshow_label"] = (np.random.rand(n) < noshow_prob).astype(int)
    return df

def train_from_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    required_cols = NUM_COLS + CAT_COLS + [TEXT_COL, "disease_label", "noshow_label"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    disease_model, noshow_model = build_models()

    X = df[NUM_COLS + CAT_COLS + [TEXT_COL]]
    y_d = df["disease_label"].astype(int)
    y_n = df["noshow_label"].astype(int)

    disease_model.fit(X, y_d)
    noshow_model.fit(X, y_n)

    # quick validation
    try:
        d_auc = roc_auc_score(y_d, disease_model.predict_proba(X)[:,1])
        n_auc = roc_auc_score(y_n, noshow_model.predict_proba(X)[:,1])
    except Exception:
        d_auc, n_auc = float("nan"), float("nan")

    dump(disease_model, DISEASE_MODEL_PATH)
    dump(noshow_model, NOSHOW_MODEL_PATH)
    dump({"num": NUM_COLS, "cat": CAT_COLS, "text": TEXT_COL}, FEATURES_META_PATH)

    return {"disease_auc": float(d_auc), "noshow_auc": float(n_auc)}

def ensure_models():
    if DISEASE_MODEL_PATH.exists() and NOSHOW_MODEL_PATH.exists():
        return
    # Train on synthetic data initially
    df = _synthetic_data(3000)
    train_from_dataframe(df)

def load_models():
    ensure_models()
    return load(DISEASE_MODEL_PATH), load(NOSHOW_MODEL_PATH)


# =========================
# FastAPI app
# =========================
app = FastAPI(
    title="Intelligent Medical Appointment Management API",
    description=(
        "Prevents health risks by estimating disease risk and attendance propensity, "
        "then recommending scheduling and engagement actions."
    ),
    version="1.0.0",
)

@app.on_event("startup")
def _startup():
    ensure_models()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    disease_model, noshow_model = load_models()

    X = to_dataframe(req.patient)
    disease_risk = float(disease_model.predict_proba(X)[0, 1])
    no_show = float(noshow_model.predict_proba(X)[0, 1])

    score = composite_priority(disease_risk, no_show)
    actions = recommend_actions(disease_risk, no_show, req.patient)

    # Simple human-readable explanations (model-agnostic heuristic)
    exp = {
        "key_factors_hint": [
            "Age, chronic conditions, and symptom patterns drive disease risk.",
            "Lead time, past no-show rate, evening/Fri/Sat slots, and distance drive no-show."
        ],
        "note": "For production, plug in SHAP/LIME with the pipeline to surface per-feature attributions."
    }

    return PredictResponse(
        disease_risk=round(disease_risk, 4),
        no_show_probability=round(no_show, 4),
        priority_score=round(score, 2),
        recommended_actions=actions,
        explanation=exp
    )

@app.post("/schedule", response_model=ScheduleResponse)
def schedule(req: ScheduleRequest):
    """
    Score each candidate slot by adjusting the patient's no-show probability
    using slot heuristics, while preserving disease-driven urgency.
    """
    disease_model, noshow_model = load_models()

    baseX = to_dataframe(req.patient)
    disease_risk = float(disease_model.predict_proba(baseX)[0, 1])
    base_noshow = float(noshow_model.predict_proba(baseX)[0, 1])

    scored = []
    for slot in req.candidate_slots:
        weekday = slot.get("weekday", req.patient.weekday)
        tod = slot.get("time_of_day", req.patient.time_of_day)

        adj = slot_attendance_adjustment(weekday, tod)
        slot_noshow = float(np.clip(base_noshow * adj, 0, 1))
        # We want high-priority *and* low no-show → blend:
        slot_priority = composite_priority(disease_risk, slot_noshow)
        # Penalize no-show more when disease risk is high (we really want them to attend)
        penalty = (slot_noshow * 30.0) * (0.5 + 0.5 * disease_risk)
        final_score = slot_priority - penalty

        scored.append({
            "slot": slot,
            "adjusted_no_show": round(slot_noshow, 4),
            "priority_component": round(slot_priority, 2),
            "final_score": round(final_score, 2),
        })

    scored.sort(key=lambda x: x["final_score"], reverse=True)
    rationale = (
        "Selected slot that maximizes clinical priority while minimizing predicted no-show. "
        "Morning and mid-week are generally favored unless historical data indicates otherwise."
    )

    return ScheduleResponse(
        best_slot=scored[0]["slot"],
        slot_scores=scored,
        rationale=rationale
    )

@app.post("/train/csv")
async def train_csv(file: UploadFile = File(...)):
    """
    Retrain both models from a CSV you provide.

    Required columns:
      - Numeric: age, chronic_conditions_count, previous_no_show_rate, days_until_appointment, sms_reminders_sent, distance_km
      - Categorical: sex, time_of_day, weekday, doctor_specialty
      - Text: symptoms_text
      - Labels: disease_label (0/1), noshow_label (0/1)
    """
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read CSV: {e}")

    try:
        metrics = train_from_dataframe(df)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status": "trained",
        "metrics": metrics,
        "note": "Models saved and hot-reloaded for subsequent /predict calls."
    }
