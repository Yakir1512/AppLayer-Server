# test_smoke.py
import time, threading
import sys
import os

# --- קוד לתיקון נתיב הייבוא (נשאר, חיוני) ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, project_root)
# ----------------------------------------------------------------------


def start_server():
    # *** התיקון: מעבירים את ייבוא server לתוך הפונקציה ***
    import server 
    server.serve("127.0.0.1", 5599, 16) 

def test_calc_and_cache():
    t = threading.Thread(target=start_server, daemon=True); t.start()
    
    # התיקון ל-WinError 10061: הגדלת זמן ההמתנה
    time.sleep(1.0) 
    
    # *** התיקון: מעבירים את ייבוא client לתוך הפונקציה ***
    import client
    
    # טסט ראשון (Miss)
    r1 = client.request("127.0.0.1", 5599, {"mode":"calc","data":{"expr":"sin(0)"},"options":{"cache":True}})
    assert r1["ok"] and abs(r1["result"] - 0.0) < 1e-9
    
    # טסט שני (Hit)
    r2 = client.request("127.0.0.1", 5599, {"mode":"calc","data":{"expr":"sin(0)"},"options":{"cache":True}})
    assert r2["ok"] and abs(r2["result"] - 0.0) < 1e-9
    assert r2["meta"]["from_cache"] is True 

if __name__ == "__main__":
    try:
        test_calc_and_cache()
        print("OK: Calculator and Cache Test Passed")
    except AssertionError:
        print("FAILED: Calculator or Cache Test Failed")
    except Exception as e:
        print(f"FAILED: An unexpected error occurred: {e}")