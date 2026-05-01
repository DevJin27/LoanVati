"""FastAPI routes for model scoring and lending report generation."""

import json
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request, Security
from fastapi.security.api_key import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.agent.graph import run_agent
from src.api.schemas import (
    HealthResponse,
    ModelInfoResponse,
    PredictionRequest,
    PredictionResponse,
    PreprocessResponse,
    ReportResponse,
)
from src.models.predict import CreditRiskPredictor
from src.preprocessing.dataset import PHASE_ROOT, resolve_processed_dir
from src.preprocessing.pipeline import build_full_feature_matrix

router = APIRouter(prefix="/api/v1")
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
APP_STARTED_AT = time.time()


def _rate_limit_key(request: Request) -> str:
    return request.headers.get("X-API-Key") or get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key)


async def verify_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> None:
    """Reject requests without the configured API key."""
    expected_key = os.getenv("API_SECRET_KEY")
    if not expected_key or api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@lru_cache
def get_predictor() -> CreditRiskPredictor:
    """Load the trained predictor once for API reuse."""
    return CreditRiskPredictor(models_path=PHASE_ROOT / "models")


def _metrics_payload() -> dict:
    metrics_path = PHASE_ROOT / "models" / "eval_metrics.json"
    return json.loads(metrics_path.read_text())


def _model_version() -> str:
    threshold_path = PHASE_ROOT / "models" / "threshold.json"
    if threshold_path.exists():
        return json.loads(threshold_path.read_text()).get("model_version", "rf_v2.0")
    return "rf_v2.0"


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Return API liveness metadata."""
    return HealthResponse(
        status="ok",
        model_version=_model_version(),
        uptime_seconds=round(time.time() - APP_STARTED_AT, 2),
    )


@router.get("/model/info", response_model=ModelInfoResponse)
async def model_info() -> ModelInfoResponse:
    """Expose tracked evaluation metrics for the frontend."""
    return ModelInfoResponse(**_metrics_payload())


@router.post("/predict", response_model=PredictionResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def predict(request: Request, payload: PredictionRequest) -> PredictionResponse:
    """Run ML inference only."""
    prediction = get_predictor().predict(payload.features)
    return PredictionResponse(**prediction)


@router.post("/report", response_model=ReportResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def report(request: Request, payload: PredictionRequest) -> ReportResponse:
    """Run ML inference followed by the agentic report pipeline."""
    prediction = get_predictor().predict(payload.features)
    agent_state = run_agent(payload.features, prediction)
    return ReportResponse(
        applicant_id=payload.applicant_id,
        prediction=PredictionResponse(**prediction),
        report=agent_state["final_report"] or {},
        processing_steps=agent_state["processing_steps"],
        error_flags=agent_state["error_flags"],
    )


@router.post(
    "/preprocess",
    response_model=PreprocessResponse,
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit("10/minute")
async def preprocess(request: Request) -> PreprocessResponse:
    """Rebuild the processed training parquet for debugging or refresh runs."""
    features, target = build_full_feature_matrix()
    processed_dir = resolve_processed_dir()
    processed_dir.mkdir(parents=True, exist_ok=True)
    output_path = processed_dir / "train_processed.parquet"
    features.assign(TARGET=target).to_parquet(output_path)
    return PreprocessResponse(
        output_path=str(output_path),
        rows=int(features.shape[0]),
        columns=int(features.shape[1]),
    )
