import requests
import os
import time

URL = 'http://127.0.0.1:5000/upload_chunk'
FILENAME = 'test_small.bin'

# Create a small test file (~5MB)
with open(FILENAME, 'wb') as f:
    f.write(os.urandom(5 * 1024 * 1024))

chunk_size = 2 * 1024 * 1024
file_size = os.path.getsize(FILENAME)
total_chunks = (file_size + chunk_size - 1) // chunk_size

print(f"Uploading {FILENAME} as {total_chunks} chunks to {URL}")

with open(FILENAME, 'rb') as f:
    for index in range(total_chunks):
        start = index * chunk_size
        f.seek(start)
        data = f.read(chunk_size)
        files = {'chunk': (f'{FILENAME}.part{index}', data)}
        form = {
            'filename': FILENAME,
            'chunk_index': str(index),
            'total_chunks': str(total_chunks)
        }
        try:
            resp = requests.post(URL, files=files, data=form, timeout=10)
            try:
                j = resp.json()
            except Exception:
                print(f"Chunk {index}: non-json response status {resp.status_code}: {resp.text}")
                break
            print(f"Chunk {index}: status={resp.status_code}, json={j}")
        except Exception as e:
            print(f"Chunk {index}: Exception during upload: {e}")
        time.sleep(0.2)

print('Done')
