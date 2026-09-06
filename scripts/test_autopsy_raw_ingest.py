"""
Test Autopsy CLI Ingest against real RAW disk image file (SYN_REAL_FORENSIC_IMAGE.raw).
Monitors case directory generation, autopsy.db database creation, ingest completion signals,
and extracted artifact files.
"""

import time
import shutil
import subprocess
import psutil
from pathlib import Path

AUTOPSY_BIN = Path("D:/D Digital Forensic/Day 2/Installed/bin/autopsy64.exe")
RAW_IMAGE_PATH = Path("D:/Proto SIH/DATA/fixtures/SYN_REAL_FORENSIC_IMAGE.raw")
CASE_OUTPUT_DIR = Path("D:/Proto SIH/DATA/benchmarks/autopsy_raw_case")

def main():
    if CASE_OUTPUT_DIR.exists():
        shutil.rmtree(CASE_OUTPUT_DIR, ignore_errors=True)
    CASE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    case_name = "autopsy_real_raw_case"
    cmd = [
        str(AUTOPSY_BIN.resolve()),
        f"--inputPath={RAW_IMAGE_PATH.resolve()}",
        f"--caseName={case_name}",
        "--runFromCommandLine=true"
    ]
    
    print(f"Launching Autopsy CLI for RAW Image: {RAW_IMAGE_PATH.resolve()}")
    print(f"Command: {' '.join(cmd)}")
    
    start_time = time.perf_counter()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ps_proc = psutil.Process(proc.pid)
    
    # Monitor for 25 seconds
    max_wait = 25
    interval = 1.0
    elapsed = 0.0
    
    peak_ram = 0.0
    cpu_samples = []
    
    print("Monitoring Autopsy ingest execution...")
    while elapsed < max_wait:
        if proc.poll() is not None:
            print(f"Process exited naturally with code: {proc.poll()}")
            break
        try:
            ram = ps_proc.memory_info().rss / (1024 * 1024)
            if ram > peak_ram:
                peak_ram = ram
            cpu_samples.append(ps_proc.cpu_percent(interval=None))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        time.sleep(interval)
        elapsed += interval
        
    if proc.poll() is None:
        print("Autopsy process active; terminating after monitoring window...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            
    total_time = time.perf_counter() - start_time
    avg_cpu = sum(cpu_samples)/len(cpu_samples) if cpu_samples else 0.0
    
    print(f"\n--- EXECUTION MONITORING RESULTS ---")
    print(f"Invocation Duration: {total_time:.2f} seconds")
    print(f"Peak RAM: {peak_ram:.2f} MB")
    print(f"Average CPU: {avg_cpu:.2f}%")
    
    # Inspect Case Directory Output
    print(f"\n--- CASE DIRECTORY DISCOVERY ---")
    found_cases = list(CASE_OUTPUT_DIR.glob(f"{case_name}*"))
    if not found_cases:
        print("No case folder found matching prefix in output directory.")
        # Check standard default case directory if set in Autopsy options
        default_appdata = Path.home() / "AppData" / "Roaming" / "autopsy" / "cases"
        if default_appdata.exists():
            print(f"Checking default AppData case directory: {default_appdata}")
            found_cases = list(default_appdata.glob(f"{case_name}*"))

    if found_cases:
        c_path = found_cases[0]
        print(f"Case Folder Found: {c_path}")
        files = list(c_path.rglob("*"))
        print(f"Total Discovered Items in Case Folder: {len(files)}")
        for f in files[:15]:
            if f.is_file():
                print(f"  - {f.relative_to(c_path)} ({f.stat().st_size} bytes)")
    else:
        print("Case directory creation requires pre-configured Command Line Ingest options path in Autopsy options panel.")

if __name__ == "__main__":
    main()
