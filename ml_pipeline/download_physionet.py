import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "raw", "physionet"))

SETS = {
    "training_setA": ("https://physionet.org/files/challenge-2019/1.0.0/training/training_setA/", 500, 1),
    "training_setB": ("https://physionet.org/files/challenge-2019/1.0.0/training/training_setB/", 500, 100001)
}

def download_patient(base_url: str, dest_dir: str, patient_idx: int):
    filename = f"p{patient_idx:06d}.psv"
    url = base_url + filename
    dest_path = os.path.join(dest_dir, filename)
    
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 100:
        return True
        
    try:
        urllib.request.urlretrieve(url, dest_path)
        return True
    except Exception:
        return False

def download_set(set_name: str, base_url: str, count: int, start_idx: int):
    dest_dir = os.path.join(BASE_DIR, set_name)
    os.makedirs(dest_dir, exist_ok=True)
    print(f"Downloading {count} patient records for {set_name} into {dest_dir}...")
    
    completed = 0
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(download_patient, base_url, dest_dir, i) for i in range(start_idx, start_idx + count)]
        for f in as_completed(futures):
            if f.result():
                completed += 1
            sys.stdout.write(f"\r  [{set_name}] Downloaded {completed}/{count} patient records...")
            sys.stdout.flush()
    print(f"\nCompleted {set_name} download.")

def main():
    os.makedirs(BASE_DIR, exist_ok=True)
    for set_name, (base_url, count, start_idx) in SETS.items():
        download_set(set_name, base_url, count, start_idx)

if __name__ == "__main__":
    main()
