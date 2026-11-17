#!/usr/bin/env python3
"""Re-record narration lines with ElevenLabs (voice "Stuart", eleven_multilingual_v2).

  ELEVENLABS_API_KEY=... python3 narrate.py s6 s8      # re-record those lines from script.json into vo/
  ELEVENLABS_API_KEY=... python3 narrate.py --all

The key is read from the environment and never written anywhere. After re-recording, check each clip's length:
scenes are timed to the clips (timeline.json), so a much longer clip needs its scene's on-screen timings adjusted
in video.html before rendering.
"""
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
VOICE = "HDA9tsk27wYi3uq0fPcK"
SETTINGS = {"stability": 0.42, "similarity_boost": 0.8, "style": 0.25, "use_speaker_boost": True}


def main() -> None:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        sys.exit("set ELEVENLABS_API_KEY")
    lines = {s["id"]: s["text"] for s in json.loads((HERE / "script.json").read_text())}
    ids = list(lines) if sys.argv[1:] == ["--all"] else sys.argv[1:]
    for i in ids:
        body = json.dumps({"text": lines[i], "model_id": "eleven_multilingual_v2", "voice_settings": SETTINGS}).encode()
        req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}?output_format=mp3_44100_128", data=body,
                                     headers={"xi-api-key": key, "Content-Type": "application/json"})
        (HERE / "vo" / f"{i}.mp3").write_bytes(urllib.request.urlopen(req, timeout=120).read())
        secs = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(HERE / "vo" / f"{i}.mp3")],
                              capture_output=True, text=True).stdout.strip()
        print(f"{i}: {secs} s")


if __name__ == "__main__":
    main()
