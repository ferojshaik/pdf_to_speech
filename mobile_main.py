#!/usr/bin/env python3
"""
Mobile-friendly PDF to Speech Converter
Optimized for Android Termux
"""

import os
import sys
import json
import logging
import re
import time
from pathlib import Path
from typing import List

# PDF processing
try:
    from pdfminer.high_level import extract_text
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("PDF processing not available. Install with: pip install pdfminer.six")

# TTS
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("TTS not available. Install with: pip install pyttsx3")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
LOG = logging.getLogger("pdf_tts_mobile")

def get_pdf_files():
    """Get list of PDF files in current directory"""
    pdf_files = list(Path('.').glob('*.pdf'))
    if not pdf_files:
        print("No PDF files found in current directory.")
        print("Please copy PDF files to this directory first.")
        return []
    return pdf_files

def select_pdf():
    """Let user select a PDF file"""
    pdf_files = get_pdf_files()
    if not pdf_files:
        return None
    
    print("\nAvailable PDF files:")
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"{i}. {pdf_file.name}")
    
    while True:
        try:
            choice = input(f"\nSelect PDF file (1-{len(pdf_files)}): ")
            index = int(choice) - 1
            if 0 <= index < len(pdf_files):
                return pdf_files[index]
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a number.")
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)

def read_pdf_pages(pdf_path: Path) -> List[str]:
    """Extract text from PDF as list of pages"""
    if not PDF_AVAILABLE:
        print("PDF processing not available!")
        return []
    
    print(f"Extracting text from {pdf_path.name}...")
    try:
        full_text = extract_text(str(pdf_path)) or ""
        pages = full_text.split("\f")
        pages = [p for p in pages if p.strip() != ""]
        print(f"Found {len(pages)} pages of text.")
        return pages
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return []

def normalize_text(txt: str) -> str:
    """Clean up text formatting"""
    txt = txt.replace("\r", "\n")
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    txt = "\n".join(line.strip() for line in txt.splitlines())
    return txt.strip()

def split_into_chunks(text: str, max_chars: int = 1000) -> List[str]:
    """Split text into TTS-friendly chunks"""
    text = text.strip()
    if not text:
        return []
    
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    buf = []
    
    def flush_buf():
        if buf:
            chunks.append(" ".join(buf).strip())
            buf.clear()
    
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        
        if len(s) > max_chars:
            start = 0
            while start < len(s):
                end = min(start + max_chars, len(s))
                chunks.append(s[start:end])
                start = end
            continue
        
        tentative = (" ".join(buf + [s])).strip()
        if len(tentative) <= max_chars:
            buf.append(s)
        else:
            flush_buf()
            buf.append(s)
    
    flush_buf()
    return [c for c in chunks if c.strip()]

def init_tts_engine():
    """Initialize TTS engine"""
    if not TTS_AVAILABLE:
        print("TTS not available!")
        return None
    
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        
        print(f"Available voices: {len(voices)}")
        for i, voice in enumerate(voices):
            name = getattr(voice, 'name', f'Voice {i}')
            print(f"  {i}: {name}")
        
        # Set default voice
        if voices:
            engine.setProperty('voice', voices[0].id)
        
        engine.setProperty('rate', 175)
        engine.setProperty('volume', 1.0)
        
        return engine
    except Exception as e:
        print(f"Error initializing TTS: {e}")
        return None

def save_text_to_file(text: str, output_path: Path):
    """Save text to file (fallback when TTS is not available)"""
    try:
        output_path.write_text(text, encoding='utf-8')
        print(f"Text saved to: {output_path}")
    except Exception as e:
        print(f"Error saving text: {e}")

def convert_pdf_to_speech(pdf_path: Path, output_dir: Path):
    """Convert PDF to speech"""
    output_dir.mkdir(exist_ok=True)
    
    # Initialize TTS
    engine = init_tts_engine()
    
    # Extract pages
    pages = read_pdf_pages(pdf_path)
    if not pages:
        print("No text found in PDF.")
        return
    
    print(f"\nConverting {len(pages)} pages...")
    
    for i, page_text in enumerate(pages, 1):
        if not page_text.strip():
            continue
        
        print(f"Processing page {i}/{len(pages)}...")
        
        # Normalize text
        text = normalize_text(page_text)
        if not text:
            continue
        
        # Split into chunks
        chunks = split_into_chunks(text)
        
        # Save each chunk
        for j, chunk in enumerate(chunks):
            if engine:
                # Try to generate audio
                try:
                    output_file = output_dir / f"page_{i:04d}_chunk_{j+1:02d}.wav"
                    engine.save_to_file(chunk, str(output_file))
                    engine.runAndWait()
                    print(f"  Audio saved: {output_file.name}")
                except Exception as e:
                    print(f"  TTS failed, saving as text: {e}")
                    output_file = output_dir / f"page_{i:04d}_chunk_{j+1:02d}.txt"
                    save_text_to_file(chunk, output_file)
            else:
                # Save as text file
                output_file = output_dir / f"page_{i:04d}_chunk_{j+1:02d}.txt"
                save_text_to_file(chunk, output_file)
    
    print(f"\nConversion complete! Files saved in: {output_dir}")

def main():
    """Main function"""
    print("=" * 50)
    print("PDF to Speech Converter - Mobile Version")
    print("=" * 50)
    
    # Check dependencies
    if not PDF_AVAILABLE:
        print("ERROR: PDF processing not available!")
        print("Install with: pip install pdfminer.six")
        return
    
    # Select PDF
    pdf_path = select_pdf()
    if not pdf_path:
        return
    
    # Create output directory
    output_dir = Path("output")
    
    # Convert
    try:
        convert_pdf_to_speech(pdf_path, output_dir)
    except KeyboardInterrupt:
        print("\nConversion interrupted by user.")
    except Exception as e:
        print(f"Error during conversion: {e}")

if __name__ == "__main__":
    main()
