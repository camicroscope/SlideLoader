import requests
import base64
import hashlib
import threading
import time
import os

SERVER = "http://localhost:5000"   # Change if needed
TESTFILE = "Path_of_file"

# --------- Create a large test file (20MB) ----------
if not os.path.exists(TESTFILE):
    with open(TESTFILE, "wb") as f:
        f.write(os.urandom(20 * 1024 * 1024))
print(f"Using test file: {TESTFILE}")

# Compute SHA256
with open(TESTFILE, "rb") as f:
    ORIGINAL_SHA = hashlib.sha256(f.read()).hexdigest().upper()

print("Original SHA256:", ORIGINAL_SHA)


# ---------------- Helper functions -----------------------

def start_upload():
    r = requests.post(f"{SERVER}/upload/start", json={"filename": TESTFILE})
    token = r.json()["upload_token"]
    return token

def send_chunk(token, offset, data):
    body = {
        "offset": offset,
        "data": base64.b64encode(data).decode()
    }
    r = requests.post(f"{SERVER}/upload/continue/{token}", json=body)
    return r.status_code, r.json()


# ------------------------- TEST 1 -------------------------
print("\n=== TEST 1: Out-of-order upload should FAIL ===")
token = start_upload()

with open(TESTFILE, "rb") as f:
    data = f.read()

chunk_size = 1024 * 1024
chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]

# Send chunk 0 (correct)
status, resp = send_chunk(token, 0, chunks[0])
print("Chunk 0:", status, resp)

# Send chunk 2 BEFORE chunk 1 → MUST FAIL (409)
status, resp = send_chunk(token, chunk_size * 2, chunks[2])
print("Out-of-order chunk (expected 409):", status, resp)

if status == 409:
    print("✔ Server correctly rejected out-of-order chunk")
else:
    print("❌ SERVER IS STILL VULNERABLE!")
    exit()

# ------------------------- TEST 2 -------------------------
print("\n=== TEST 2: Parallel uploads MUST trigger 409 ===")

token = start_upload()

threads = []
results = []

def worker(i, blob):
    # ALL threads intentionally send WRONG offset (0)
    status, resp = send_chunk(token, 0, blob)
    results.append((i, status))

for i in range(10):
    t = threading.Thread(target=worker, args=(i, chunks[0]))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print("Parallel responses:", results)

if any(s == 409 for _, s in results):
    print("✔ Server correctly rejects parallel uploads")
else:
    print("❌ Server allowed multiple writes → still broken")


# ------------------------- TEST 3 -------------------------
print("\n=== TEST 3: Full Upload With Resume Must Match SHA ===")

token = start_upload()

offset = 0
i = 0

while offset < len(data):
    chunk = chunks[i]
    status, resp = send_chunk(token, offset, chunk)

    if status == 409:
        # Server tells us "expected_offset"
        offset = resp["expected_offset"]
        continue

    offset += len(chunk)
    i += 1

# FINISH
r = requests.post(f"{SERVER}/upload/finish/{token}", json={
    "filename": "uploaded_test.bin",
    "sha256": ORIGINAL_SHA,
    "size": len(data)
})

print("Finish response:", r.status_code, r.json())

if r.status_code == 200:
    print("✔ Full upload completed with correct SHA")
else:
    print("❌ Final SHA mismatch → file corrupted")
