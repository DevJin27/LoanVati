import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv(dotenv_path="/Users/Personal/Desktop/EVERYTHING/LoanVati/phase-2/.env", override=True)
api_key = os.getenv("GROQ_API_KEY")

prompt_sys = """You are a senior credit risk officer explaining why a borrower received a model-driven risk score.
Use ONLY the supplied borrower summary, the numeric risk score, the risk class, and the SHAP features.
Do not fabricate financial facts or cite regulations in this step.
If the risk score is between 0.40 and 0.60, explicitly mention uncertainty.
Return ONLY valid JSON in this exact schema:
{
  "risk_analysis": "<200 words or fewer>",
  "retrieval_query": "<10-15 word regulatory retrieval query>"
}"""

prompt_user = """Borrower Summary: They are employed.
ML Risk Score: 0.36
Risk Class: Low
Top Risk-Driving Features:
[]"""

llm = ChatGroq(groq_api_key=api_key, model="llama-3.3-70b-versatile", temperature=0.0, max_tokens=2048)
try:
    res = llm.invoke([("system", prompt_sys), ("user", prompt_user)])
    print("RAW OUTPUT:")
    print(repr(res.content))
except Exception as e:
    print("FAILED:", str(e))
