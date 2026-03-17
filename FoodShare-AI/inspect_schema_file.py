import os
import json
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE") or os.environ.get("SUPABASE_KEY")

sb = create_client(url, key)

result = {}
try:
    res = sb.table("donations").select("*").limit(1).execute()
    if res.data:
        result["columns"] = list(res.data[0].keys())
    else:
        result["columns"] = "No data"
        try:
            sb.table("donations").insert({"invalid_column_test": 1}).execute()
        except Exception as e:
            result["error"] = str(e)
except Exception as e:
    result["error"] = str(e)

with open("schema_inspect.json", "w") as f:
    json.dump(result, f, indent=2)
