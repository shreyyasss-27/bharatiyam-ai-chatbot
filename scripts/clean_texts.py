#!/usr/bin/env python3
import os
import re
from pathlib import Path
from tqdm import tqdm

def clean_text(text):
    # Remove non-devanagari and non-english characters (keep spaces and basic punctuation)
    cleaned = re.sub(r'[^\u0900-\u097F\u0000-\u007F\s\.,;:!?()\[\]{}]', '', text)
    # Remove multiple spaces and newlines
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def clean_text_files(input_dir, output_dir):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    text_files = list(input_dir.glob('*.txt'))
    if not text_files:
        print(f"No text files found in {input_dir}")
        return
    
    print(f"Cleaning {len(text_files)} text files...")
    for i, file_path in enumerate(tqdm(text_files, desc="Processing files")):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Clean the content
            cleaned_content = clean_text(content)
            
            # Save cleaned content
            output_path = output_dir / f"cleaned_{i+1}.txt"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
                
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
    
    print(f"Cleaned files saved to {output_dir}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python clean_texts.py <input_dir> <output_dir>")
        sys.exit(1)
    
    clean_text_files(sys.argv[1], sys.argv[2])
