import time
import threading

nonce_store = {}
nonce_lock = threading.Lock()
TTL_SECONDS = 10

def cleanup_loop():
    """Background thread that sweeps expired nonces every few seconds."""
    while True:
        time.sleep(TTL_SECONDS)
        current_time = time.time()
        with nonce_lock:
            expired = [k for k, exp in nonce_store.items() if exp < current_time]
            for k in expired:
                del nonce_store[k]

# Start the background thread as a daemon
cleaner_thread = threading.Thread(target=cleanup_loop, daemon=True)
cleaner_thread.start()

def add_nonce(nonce):
    with nonce_lock:
        nonce_store[nonce] = time.time() + TTL_SECONDS

def use_nonce(nonce):
    with nonce_lock:
        if nonce in nonce_store:
            del nonce_store[nonce]
            return True
        return False