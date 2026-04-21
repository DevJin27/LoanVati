import os
import tempfile
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, "/Users/Personal/Desktop/EVERYTHING/LoanVati/phase-2")
load_dotenv("/Users/Personal/Desktop/EVERYTHING/LoanVati/phase-2/.env", override=True)

from src.agent.graph import run_agent

borrower_data = {
    'AMT_INCOME_TOTAL': 180000.0, 'AMT_CREDIT': 500000.0, 'AMT_ANNUITY': 42000.0, 
    'CNT_FAM_MEMBERS': 2.0, 'DAYS_BIRTH': -14000.0, 'DAYS_EMPLOYED': -1825.0, 
    'NAME_INCOME_TYPE': 'Working', 'NAME_EDUCATION_TYPE': 'Higher education', 
    'NAME_FAMILY_STATUS': 'Married', 'NAME_HOUSING_TYPE': 'House / apartment'
}
prediction = {
    'risk_score': 0.36, 
    'risk_class': 'Low', 
    'top_features': [{'feature': 'DAYS_BIRTH', 'direction': 'decreases risk', 'shap_value': -0.1}]
}

try:
    state = run_agent(borrower_data, prediction)
    print("ERRORS:", state['error_flags'])
except Exception as e:
    print("FATAL ERROR:", str(e))
    raise e

if os.path.exists("/tmp/llm_debug_raw.log"):
    print("\n--- LLM DEBUG OUTPUT ---")
    with open("/tmp/llm_debug_raw.log", "r") as f:
        print(f.read())
