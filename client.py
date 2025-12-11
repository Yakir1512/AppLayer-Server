# client.py
import argparse, socket, json, sys

def get_calc_expression() -> str:
    """
    מציג תפריט של ביטויים מתמטיים מוגדרים מראש או מאפשר קלט חופשי.
    """
    PREDEFINED_EXPRS = [
        "2 * (4 + 6)",
        "sqrt(9) + tan(0)",
        "5**2 + 3 * log(e)"
    ]
    
    print("\n--- בחירת ביטוי מתמטי (CALC) ---")
    print("בחר ביטוי מהרשימה או הקלד ביטוי משלך:")
    
    for i, expr in enumerate(PREDEFINED_EXPRS):
        print(f"  {i + 1}. {expr}")
        
    print("  4. הקלדת ביטוי חופשי")

    while True:
        choice = input("הכנס מספר (1-4): ").strip()

        if choice.isdigit():
            idx = int(choice) - 1
            
            if 0 <= idx < len(PREDEFINED_EXPRS):
                return PREDEFINED_EXPRS[idx]
            
            elif idx == 3: # אפשרות 4 - קלט חופשי
                free_expr = input("הקלד את הביטוי האלגברי/לוגי: ").strip()
                if free_expr:
                    return free_expr
                # אם הקלט ריק, נחזור ללולאה כדי לבחור שוב
            
            else:
                print("בחירה לא חוקית. נסה שוב.")
        else:
            print("קלט לא חוקי. נסה שוב.")

def request(host: str, port: int, payload: dict) -> dict:
    """Send a single JSON-line request and return a single JSON-line response."""
    data = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    with socket.create_connection((host, port), timeout=5) as s:
        s.sendall(data)
        buff = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            buff += chunk
            if b"\n" in buff:
                line, _, _ = buff.partition(b"\n")
                return json.loads(line.decode("utf-8"))
    return {"ok": False, "error": "No response"}

def main():
    ap = argparse.ArgumentParser(description="Client (calc/gpt over JSON TCP)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5555)
    ap.add_argument("--mode", choices=["calc", "gpt"], required=True)
    ap.add_argument("--expr", help="Expression for mode=calc")
    ap.add_argument("--prompt", help="Prompt for mode=gpt")
    ap.add_argument("--no-cache", action="store_true", help="Disable caching")
    ap.add_argument("--repeat", type=int, default=1, help="Number of times to repeat the request")  #new arg to count the times
                                                                                                    #we will send te request
    args = ap.parse_args()
    payload = None

    if args.mode == "calc":
        if not args.expr:
            selected_expr = get_calc_expression()   #פונ' עזר לקבלת ביטוי מהמשתמש
            args.expr = selected_expr               #הביטוי שבתוך הקובץ לשליחה
        #אם הביטוי ריק
        if not args.expr:       
            print("לא נבחר ביטוי לחישוב.", file=sys.stderr); sys.exit(2)
        #תכניס לתוכן ההודעה    
        payload = {"mode": "calc", "data": {"expr": args.expr}, "options": {"cache": not args.no_cache}}
        #אם נבחר GPT אז תביא פרומט
    else:
        if not args.prompt:
            print("\n--- בחירת פרומפט ל-GPT ---")
            args.prompt = input("הקלד את הפרומפט שלך: ").strip()    
        
        #אם הפרומט ריק
        if not args.prompt:
            print("לא נבחר פרומפט.", file=sys.stderr); sys.exit(2)
            
        #תכניס פרומט לתוכן ההודעה
        payload = {"mode": "gpt", "data": {"prompt": args.prompt}, "options": {"cache": not args.no_cache}}
                    
       
        #לולאה לבקשות 
    for i in range(args.repeat):
        print(f"\n send request #{i + 1}/{args.repeat}...")
        
        try:
            
            resp = request(args.host, args.port, payload)
            
            
            print("--- תגובת שרת ---")
            print(json.dumps(resp, ensure_ascii=False, indent=2))
            print("-----------------")

        except Exception as e:
            # עצירה אם יש כשל בחיבור
            print(f"שגיאת חיבור או תקשורת: {e}. עוצר את הלולאה.")
            break
        
if __name__ == "__main__":
    main()

