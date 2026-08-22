"""
Downloader for PhysioNet Computing in Cardiology Challenge 2019 Sepsis Dataset.
Fetches ALL 40,336 patient records (.psv) across Set A (20,336) and Set B (20,000)
directly from PhysioNet's open AWS S3 storage.
"""

import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

DATA_BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
S3_ROOT = "https://physionet-open.s3.amazonaws.com/challenge-2019/1.0.0/training/"

def download_file(url: str, dest_path: str) -> bool:
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 100:
        return True
    try:
        urllib.request.urlretrieve(url, dest_path)
        return True
    except Exception:
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except:
                pass
        return False

def download_set_a(num_patients: int = 20336, max_workers: int = 50):
    dest_dir = os.path.join(DATA_BASE_DIR, "training_setA")
    os.makedirs(dest_dir, exist_ok=True)
    print(f"[*] Downloading ALL {num_patients} records for Training Set A (Hospital A)...", flush=True)
    
    tasks = []
    for i in range(1, num_patients + 1):
        fname = f"p{i:06d}.psv"
        url = f"{S3_ROOT}training_setA/{fname}"
        dest = os.path.join(dest_dir, fname)
        tasks.append((url, dest))
        
    run_batch(tasks, max_workers, "Set A")

def download_set_b(num_patients: int = 20000, max_workers: int = 50):
    dest_dir = os.path.join(DATA_BASE_DIR, "training_setB")
    os.makedirs(dest_dir, exist_ok=True)
    print(f"[*] Downloading ALL {num_patients} records for Training Set B (Hospital B)...", flush=True)
    
    tasks = []
    # Hospital B patient IDs start at 100001
    for i in range(100001, 100001 + num_patients):
        fname = f"p{i:06d}.psv"
        url = f"{S3_ROOT}training_setB/{fname}"
        dest = os.path.join(dest_dir, fname)
        tasks.append((url, dest))
        
    run_batch(tasks, max_workers, "Set B")

def run_batch(tasks, max_workers, set_label):
    start_time = time.time()
    successful = 0
    total = len(tasks)
    
    # Pre-check already existing valid files
    already_done = 0
    pending_tasks = []
    for url, dest in tasks:
        if os.path.exists(dest) and os.path.getsize(dest) > 100:
            already_done += 1
        else:
            pending_tasks.append((url, dest))
            
    successful = already_done
    if already_done > 0:
        print(f"    -> Found {already_done}/{total} files already downloaded.", flush=True)
        
    if not pending_tasks:
        print(f"[+] All {total} files for {set_label} are already present.\n", flush=True)
        return

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_file, url, dest): (url, dest) for url, dest in pending_tasks}
        for future in as_completed(futures):
            if future.result():
                successful += 1
                if successful % 1000 == 0 or successful == total:
                    pct = (successful / total) * 100
                    elapsed = time.time() - start_time
                    print(f"    -> [{set_label}] Downloaded {successful}/{total} files ({pct:.1f}%) in {elapsed:.1f}s...", flush=True)
                    
    elapsed = time.time() - start_time
    print(f"[+] Finished {set_label}: {successful}/{total} files ready in {elapsed:.2f}s.\n", flush=True)

if __name__ == "__main__":
    print("=== PHYSIONET 2019 FULL DATASET DOWNLOADER ===", flush=True)
    print("Total Target: 40,336 patient records (Set A: 20,336 | Set B: 20,000)", flush=True)
    download_set_a(num_patients=20336, max_workers=50)
    download_set_b(num_patients=20000, max_workers=50)
    print("=== DOWNLOAD COMPLETE ===", flush=True)
