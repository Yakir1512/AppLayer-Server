# test_smoke.py
import time, threading
import sys
import os

# --- קוד לתיקון נתיב הייבוא (חובה אם test_smoke.py בתיקיית tests) ---
# מוסיף את התיקייה הראשית (parent directory) לנתיבי החיפוש של Python.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, project_root)
# ----------------------------------------------------------------------


def start_server():
    # הייבוא יעבוד עכשיו
    import server
    # משתמש בפורט שונה מהרגיל כדי לא להתנגש עם שרת רץ
    server.serve("127.0.0.1", 5599, 16) 

def test_calc_and_cache():
    t = threading.Thread(target=start_server, daemon=True); t.start()
    time.sleep(0.3)
    
    # הייבוא יעבוד עכשיו
    import client
    
    # טסט ראשון (צריך להיות Miss)
    r1 = client.request("127.0.0.1", 5599, {"mode":"calc","data":{"expr":"sin(0)"},"options":{"cache":True}})
    assert r1["ok"] and abs(r1["result"] - 0.0) < 1e-9
    
    # טסט שני (צריך להיות Hit)
    r2 = client.request("127.0.0.1", 5599, {"mode":"calc","data":{"expr":"sin(0)"},"options":{"cache":True}})
    assert r2["ok"] and abs(r2["result"] - 0.0) < 1e-9
    assert r2["meta"]["from_cache"] is True # מוודאים שהיה שימוש במטמון

if __name__ == "__main__":
    try:
        test_calc_and_cache()
        print("OK: Calculator and Cache Test Passed")
    except AssertionError:
        print("FAILED: Calculator or Cache Test Failed")
    except Exception as e:
        print(f"FAILED: An unexpected error occurred: {e}")