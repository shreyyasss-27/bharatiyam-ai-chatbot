#!/usr/bin/env python3
# scripts/rebuild_index.py
import os
import sys
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get directories from environment variables
FAISS_DIR = Path(os.getenv("FAISS_DIR"))
TEXT_DIR = Path(os.getenv("DATA_TEXT_DIR"))

print("Rebuilding FAISS index...")

# Clean up existing index
if FAISS_DIR.exists():
    print(f"Removing existing index in {FAISS_DIR}")
    shutil.rmtree(FAISS_DIR, ignore_errors=True)

FAISS_DIR.mkdir(parents=True, exist_ok=True)

# Rebuild the index
print("Running build_index.py...")
import subprocess
subprocess.run(["python", "-m", "scripts.build_index"], check=True)

print("Index rebuilt successfully!")
print(f"Index location: {FAISS_DIR}")
