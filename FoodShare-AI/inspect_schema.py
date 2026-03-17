import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE") or os.environ.get("SUPABASE_KEY")

sb = create_client(url, key)

try:
    res = sb.table("donations").select("*").limit(1).execute()
    if res.data:
        print("COLUMNS IN DB:")
        for k in res.data[0].keys():
            print(" -", k)
    else:
        print("No data, cannot infer columns, let's trigger an error.")
        try:
            sb.table("donations").insert({"invalid_column_test": 1}).execute()
        except Exception as e:
            print("Error:", e)
except Exception as e:
    print("Failed pulling columns:", e)
