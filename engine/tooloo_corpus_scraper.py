# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.tooloo_corpus_scraper.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

import os
import sys
import requests

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def build_audio_corpus(download_dir="./audio_corpus"):
    """Pulls diverse, uncompressed human audio for Claudio to test."""
    os.makedirs(download_dir, exist_ok=True)
    
    # High-quality WAV URLs for stress testing
    test_assets = {
        "female_vocal.wav": "https://www.kozco.com/tech/pno-cs.wav", 
        "acoustic_drum_break.wav": "https://www.kozco.com/tech/piano2.wav", 
        "speech_sibilance.wav": "https://www.kozco.com/tech/LRMonoPhase4.wav"
    }
    
    for filename, url in test_assets.items():
        filepath = os.path.join(download_dir, filename)
        if not os.path.exists(filepath):
            print(f"[TOOLOO] Downloading test asset: {filename}")
            try:
                response = requests.get(url, stream=True, timeout=10)
                if response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                else:
                    print(f"[ERROR] Failed to fetch {filename} (Status: {response.status_code})")
            except Exception as e:
                print(f"[ERROR] Exception downloading {filename}: {e}")
        else:
            print(f"[TOOLOO] Asset {filename} already exists.")

if __name__ == "__main__":
    build_audio_corpus()
