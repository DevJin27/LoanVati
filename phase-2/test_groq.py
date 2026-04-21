import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv(dotenv_path="/Users/Personal/Desktop/EVERYTHING/LoanVati/phase-2/.env")
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print("NO API KEY FOUND IN .env")
elif api_key == "f":
    print("API KEY IS STILL SET TO 'f'")
else:
    print(f"Loaded API key starting with: {api_key[:8]}... (Length: {len(api_key)})")
    try:
        llm = ChatGroq(groq_api_key=api_key, model="llama-3.3-70b-versatile", max_tokens=10)
        res = llm.invoke("Hello")
        print("API CALL SUCCESSFUL!")
        print("Response:", res.content)
    except Exception as e:
        print("API CALL FAILED!")
        print(str(e))
