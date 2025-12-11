# proxy.py
import argparse, socket, threading, json

# proxy.py
import argparse, socket, threading, json, time, collections # ייבוא חדש ל-time ו-collections

# ---------------- LRU Cache (Copied from server.py) ----------------
class LRUCache:
    """Minimal LRU cache based on OrderedDict."""
    def __init__(self, capacity: int = 128):
        self.capacity = capacity
        # נשתמש ב-collections.OrderedDict כדי לשמור על סדר השימוש
        self._d = collections.OrderedDict() 

    def get(self, key):
        if key not in self._d:
            return None
        self._d.move_to_end(key) # מזיז את המפתח שנעשה בו שימוש לסוף הרשימה (הכי עדכני)
        return self._d[key]

    def set(self, key, value):
        self._d[key] = value
        self._d.move_to_end(key)
        if len(self._d) > self.capacity:
            self._d.popitem(last=False) # מוחק את הפריט שבו נעשה שימוש הכי פחות עדכני

# --- גלובלי ---
PROXY_CACHE = None
CACHE_LOCK = threading.Lock() # מנעול (Lock) להבטחת עבודה בטוחה בריבוי תהליכונים

# def pipe(src, dst):
#     """Bi-directional byte piping helper."""
#     try:
#         while True:
#             data = src.recv(4096)
#             if not data:
#                 break
#             dst.sendall(data)
#     except Exception:
#         pass
#     finally:
#         try: dst.shutdown(socket.SHUT_WR)
#         except Exception: pass
        
        
def handle_request_with_cache(c: socket.socket, sh: str, sp: int, cache: LRUCache):
    """
    מקבלת חיבור מהלקוח, קוראת את הבקשה, בודקת מטמון, ומעבירה לשרת אם צריך.
    """
    # 1. קליטת הבקשה המלאה מהלקוח (עד \n)
    try:
        raw = b""
        # מנסים לקרוא את הבקשה מהלקוח
        while True:
            chunk = c.recv(4096)
            if not chunk:
                break
            raw += chunk
            if b"\n" in raw:
                line, _, _ = raw.partition(b"\n")
                msg = json.loads(line.decode("utf-8"))
                break
        else:
            return # לא התקבלה בקשה מלאה

    except Exception as e:
        print(f"[proxy] Error reading/parsing client request: {e}")
        return # יציאה במקרה של שגיאה

    # 2. קביעת מפתח המטמון (Cache Key)
    # המפתח צריך לכלול את כל הנתונים הרלוונטיים לבקשה (mode, expr/prompt)
    key_data = msg['data']
    cache_key = (msg['mode'],) + tuple(sorted(key_data.items()))
    
    # 3. בדיקת מטמון (Cache Hit)
    with CACHE_LOCK:
        resp = cache.get(cache_key)
    
    if resp:
        # נמצא במטמון - שינוי המטא-דאטה לשקף שהתשובה הגיעה מהפרוקסי
        if resp.get('meta'):
            resp['meta']['from_proxy_cache'] = True
        
        print(f"[proxy] Cache HIT for mode={msg['mode']}. Sending cached response.")
        
    else:
        # 4. החטאת מטמון (Cache Miss) - פנייה לשרת
        print(f"[proxy] Cache MISS for mode={msg['mode']}. Forwarding to server...")
        
        server_request = (json.dumps(msg, ensure_ascii=False) + "\n").encode("utf-8")
        
        try:
            # יצירת חיבור לשרת האמיתי
            with socket.create_connection((sh, sp), timeout=5) as s:
                s.sendall(server_request)
                
                # קריאת התגובה המלאה מהשרת (עד \n)
                server_buff = b""
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    server_buff += chunk
                    if b"\n" in server_buff:
                        line, _, _ = server_buff.partition(b"\n")
                        resp = json.loads(line.decode("utf-8"))
                        break
                
            # 5. עדכון מטמון
            with CACHE_LOCK:
                # מאחסנים את התשובה שהתקבלה מהשרת
                cache.set(cache_key, resp) 

        except Exception as e:
            # שגיאה בחיבור לשרת או בקריאת התגובה
            print(f"[proxy] Error communicating with server: {e}")
            resp = {"ok": False, "error": f"Proxy failed to connect to server: {e}"}

    # 6. שליחת התגובה (מטמון או שרת) בחזרה ללקוח
    try:
        out = (json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8")
        c.sendall(out)
    except Exception as e:
        print(f"[proxy] Error sending response back to client: {e}")        

def main():
    global PROXY_CACHE
    
    ap = argparse.ArgumentParser(description="Application-level TCP proxy with Caching")
    ap.add_argument("--listen-host", default="127.0.0.1")
    ap.add_argument("--listen-port", type=int, default=5554)
    ap.add_argument("--server-host", default="127.0.0.1")
    ap.add_argument("--server-port", type=int, default=5555)
    # הוספת ארגומנט לגודל המטמון
    ap.add_argument("--cache-size", type=int, default=256, help="Capacity of the proxy cache")
    args = ap.parse_args()
    
    # אתחול המטמון
    PROXY_CACHE = LRUCache(capacity=args.cache_size)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((args.listen_host, args.listen_port))
        s.listen(16)
        print(f"[proxy] Listening on {args.listen_host}:{args.listen_port}. Caching enabled (size={args.cache_size}).")
        print(f"[proxy] Forwarding to {args.server_host}:{args.server_port}")
        
        while True:
            c, addr = s.accept()
            # מעבירים ל-handle את פרטי השרת כדי שיוכל להתחבר אליו
            threading.Thread(target=handle, args=(c, args.server_host, args.server_port), daemon=True).start()

def handle(c, sh, sp):
    with c:
        # במקום להפעיל pipe, אנו מטפלים בלוגיקת הבקשה/תשובה
        handle_request_with_cache(c, sh, sp, PROXY_CACHE)

if __name__ == "__main__":
    main()
