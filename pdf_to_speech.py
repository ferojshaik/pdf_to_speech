# pdf_to_speech.py
import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import List

# --- PDF text extraction ---
from pdfminer.high_level import extract_text

# --- TTS ---
import pyttsx3

# ----------------- Logging -----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
LOG = logging.getLogger("pdf_tts")

# ----------------- Helpers -----------------
def read_pdf_pages(pdf_path: Path) -> List[str]:
    """
    Extract text from a PDF as a list of pages.
    Uses pdfminer.six; page breaks appear as '\f'.
    """
    LOG.info("Extracting text from PDF (this may take a while for large files)…")
    full_text = extract_text(str(pdf_path)) or ""
    # Split on form-feed (page separator in pdfminer output)
    pages = full_text.split("\f")
    # Remove trailing empties
    pages = [p for p in pages if p.strip() != ""]
    LOG.info("Found %d non-empty pages of text.", len(pages))
    return pages

def normalize_text(txt: str) -> str:
    """
    Clean up spacing; preserve paragraph breaks reasonably.
    """
    # Replace multiple spaces/newlines with single equivalents
    txt = txt.replace("\r", "\n")
    txt = re.sub(r"[ \t]+", " ", txt)
    # Collapse 3+ newlines into 2 to keep paragraph feel
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    # Trim lines
    txt = "\n".join(line.strip() for line in txt.splitlines())
    return txt.strip()

def split_into_chunks(text: str, max_chars: int = 1500) -> List[str]:
    """
    Split text into chunks that are small enough for TTS engines.
    Prefer sentence boundaries, then fall back to character chunks.
    """
    text = text.strip()
    if not text:
        return []

    # First, split by sentences (rough)
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
        # If a single sentence is huge, hard-split it
        if len(s) > max_chars:
            # Split by commas/spaces without exceeding max_chars
            start = 0
            while start < len(s):
                end = min(start + max_chars, len(s))
                chunks.append(s[start:end])
                start = end
            continue

        # Try to append to buffer
        tentative = (" ".join(buf + [s])).strip()
        if len(tentative) <= max_chars:
            buf.append(s)
        else:
            flush_buf()
            buf.append(s)

    flush_buf()
    return [c for c in chunks if c.strip()]

def init_tts_engine(voice_index: int = None, rate: int = None, volume: float = 1.0):
    engine = pyttsx3.init()  # SAPI5 on Windows, NSSpeechSynth on macOS, eSpeak on Linux
    voices = engine.getProperty("voices")

    # Print available voices (once)
    LOG.info("Available voices:")
    for i, v in enumerate(voices):
        LOG.info("  [%d] name=%s | id=%s | lang=%s", i, getattr(v, "name", "?"), getattr(v, "id", "?"), getattr(v, "languages", "?"))

    if voice_index is not None:
        try:
            engine.setProperty("voice", voices[voice_index].id)
        except Exception as e:
            LOG.warning("Could not set voice index %s (%s). Using default.", voice_index, e)

    if rate is not None:
        engine.setProperty("rate", int(rate))

    if volume is not None:
        engine.setProperty("volume", float(volume))

    return engine

def tts_save(engine, text: str, out_wav: Path, retries: int = 3, sleep_sec: float = 1.0):
    """
    Save TTS to a WAV file with retries. pyttsx3 usually outputs WAV reliably.
    """
    for attempt in range(1, retries + 1):
        try:
            # Remove existing partial file if any
            if out_wav.exists():
                try:
                    out_wav.unlink()
                except Exception:
                    pass
            engine.save_to_file(text, str(out_wav))
            engine.runAndWait()
            if out_wav.exists() and out_wav.stat().st_size > 0:
                return
            raise RuntimeError("No output or zero-byte file.")
        except Exception as e:
            LOG.warning("TTS save failed (attempt %d/%d): %s", attempt, retries, e)
            time.sleep(sleep_sec)
            # Re-initialize the engine on the next attempt to avoid bad state
            if attempt < retries:
                engine.stop()
                engine = init_tts_engine(
                    voice_index=None,  # keep default on re-init; safer
                    rate=None,
                    volume=1.0,
                )
    raise RuntimeError(f"TTS failed after {retries} attempts for {out_wav.name}")

# ----------------- Checkpointing -----------------
def load_checkpoint(path: Path):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            LOG.warning("Could not read checkpoint; starting fresh.")
    return {"completed_pages": []}

def save_checkpoint(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ----------------- Main conversion -----------------
def convert_pdf_to_speech(
    pdf_path: Path,
    outdir: Path,
    voice_index: int = None,
    rate: int = 175,
    page_prefix: str = "page",
    max_chunk_chars: int = 1500,
):
    outdir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = outdir / "progress.json"

    pages = read_pdf_pages(pdf_path)
    if not pages:
        LOG.error("No extractable text found in PDF.")
        sys.exit(2)

    ckpt = load_checkpoint(checkpoint_path)
    done_pages = set(ckpt.get("completed_pages", []))

    engine = init_tts_engine(voice_index=voice_index, rate=rate, volume=1.0)

    for p_idx, raw_text in enumerate(pages, start=1):
        if p_idx in done_pages:
            LOG.info("Skipping page %d (already completed).", p_idx)
            continue

        text = normalize_text(raw_text)
        if not text:
            LOG.info("Page %d empty after cleaning — marking done.", p_idx)
            done_pages.add(p_idx)
            save_checkpoint(checkpoint_path, {"completed_pages": sorted(done_pages)})
            continue

        chunks = split_into_chunks(text, max_chars=max_chunk_chars)
        LOG.info("Page %d: %d chunk(s).", p_idx, len(chunks))

        if len(chunks) == 0:
            LOG.info("Page %d has no speakable text — marking done.", p_idx)
            done_pages.add(p_idx)
            save_checkpoint(checkpoint_path, {"completed_pages": sorted(done_pages)})
            continue

        # Produce one WAV per page; concatenate outside if you like
        page_wav = outdir / f"{page_prefix}_{p_idx:04d}.wav"

        # If page has multiple chunks, render to temp files and then concatenate WAVs
        if len(chunks) == 1:
            LOG.info("Rendering page %d → %s", p_idx, page_wav.name)
            tts_save(engine, chunks[0], page_wav)
        else:
            LOG.info("Rendering page %d in %d parts…", p_idx, len(chunks))
            for i, chunk in enumerate(chunks, start=1):
                part = outdir / f"{page_prefix}_{p_idx:04d}_part_{i:02d}.wav"
                tts_save(engine, chunk, part)


                # Mark page done
                done_pages.add(p_idx)
                save_checkpoint(checkpoint_path, {"completed_pages": sorted(done_pages)})

            LOG.info("All done! WAV files saved in: %s", outdir.resolve())


def concat_wavs(parts: List[Path], out_path: Path):
    """
    Concatenate WAV files with native wave module (no ffmpeg dependency).
    Assumes all inputs share the same audio params (pyttsx3 produces consistent params).
    """
    import wave

    if not parts:
        raise ValueError("No parts to concatenate.")
    params = None
    frames = []

    for p in parts:
        with wave.open(str(p), "rb") as w:
            if params is None:
                params = w.getparams()
            else:
                if w.getparams() != params:
                    raise RuntimeError("Mismatched WAV params; cannot concatenate.")
            frames.append(w.readframes(w.getnframes()))

    with wave.open(str(out_path), "wb") as out:
        out.setparams(params)
        for fr in frames:
            out.writeframes(fr)

# ----------------- CLI -----------------
def parse_args():
    ap = argparse.ArgumentParser(
        description="Convert a PDF book to speech (one WAV per page) with resume-safe checkpoints."
    )
    ap.add_argument("pdf", type=str, help="Path to the input PDF.")
    ap.add_argument("--outdir", type=str, default="tts_output", help="Output folder for WAV files.")
    ap.add_argument("--voice", type=int, default=None, help="Voice index to use (see printed list).")
    ap.add_argument("--rate", type=int, default=175, help="Speech rate (words per minute).")
    ap.add_argument("--chunk", type=int, default=1500, help="Max characters per TTS chunk.")
    return ap.parse_args()

def main():
    args = parse_args()
    pdf_path = Path(args.pdf).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()

    if not pdf_path.exists():
        LOG.error("PDF not found: %s", pdf_path)
        sys.exit(1)

    try:
        convert_pdf_to_speech(
            pdf_path=pdf_path,
            outdir=outdir,
            voice_index=args.voice,
            rate=args.rate,
            max_chunk_chars=args.chunk,
        )
    except KeyboardInterrupt:
        LOG.warning("Interrupted by user. Progress saved; you can rerun to resume.")
    except Exception as e:
        LOG.exception("Failed: %s", e)
        sys.exit(3)

if __name__ == "__main__":
    main()
