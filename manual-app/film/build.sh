#!/usr/bin/env bash
# Mix narration over the music (ducking the music under the voice), then encode the film.
#   ./build.sh out        (after render.js has written out/f/*.jpg, out/music.pcm and out/timeline.json)
# Writes out/manual-handling.mp4 (full quality) and out/web.mp4 (the copy the website plays).
set -euo pipefail
OUT=${1:-out}; HERE=$(cd "$(dirname "$0")" && pwd)
python3 - "$OUT" "$HERE" <<'PY'
import json, subprocess, sys
out, here = sys.argv[1], sys.argv[2]
tl = json.load(open(f"{out}/timeline.json")); order = ["s1", "s2", "s3", "s4", "s5", "ux", "s6", "s7", "s8"]
cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", "44100", "-ac", "2", "-i", f"{out}/music.pcm"]
for o in order: cmd += ["-i", f"{here}/vo/{o}.mp3"]
fc = [f"[{i+1}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={int(st*1000)}|{int(st*1000)}[v{i}]" for i, st in enumerate(tl["START"])]
fc.append("".join(f"[v{i}]" for i in range(9)) + "amix=inputs=9:normalize=0,volume=1.5,asplit=2[vo][key]")
fc.append("[0:a]volume=0.55[m];[m][key]sidechaincompress=threshold=0.02:ratio=8:attack=40:release=700[duck]")
fc.append(f"[duck][vo]amix=inputs=2:normalize=0,alimiter=limit=0.95,apad=whole_dur={tl['TOTAL']:.2f},loudnorm=I=-16:TP=-1.5:LRA=11[out]")
cmd += ["-filter_complex", ";".join(fc), "-map", "[out]", "-ar", "44100", "-c:a", "pcm_s16le", f"{out}/mixn.wav"]
subprocess.run(cmd, check=True)
PY
T=$(python3 -c "import json;print(json.load(open('$OUT/timeline.json'))['TOTAL'])")
ffmpeg -y -loglevel error -framerate 30 -i "$OUT/f/%05d.jpg" -i "$OUT/mixn.wav" -c:v libx264 -preset medium -crf 21 -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart -t "$T" "$OUT/manual-handling.mp4"
ffmpeg -y -loglevel error -i "$OUT/manual-handling.mp4" -c:v libx264 -preset slow -b:v 640k -maxrate 900k -bufsize 1800k -pix_fmt yuv420p -c:a aac -b:a 112k -movflags +faststart "$OUT/web.mp4"
ffmpeg -y -loglevel error -ss 11.2 -i "$OUT/manual-handling.mp4" -frames:v 1 "$OUT/poster.jpg"
echo "wrote $OUT/manual-handling.mp4, $OUT/web.mp4, $OUT/poster.jpg"
