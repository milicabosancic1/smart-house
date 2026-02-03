import time

def ts():
    t = time.localtime()
    return time.strftime('%H:%M:%S', t)

def banner(code: str):
    print("=" * 26)
    print(f"Timestamp: {ts()}")
    print(f"Code: {code}")
