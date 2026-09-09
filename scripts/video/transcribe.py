import json, os, sys, glob
from faster_whisper import WhisperModel

import sys
W = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(f"{W}/transcripts", exist_ok=True)

model = WhisperModel("small", device="cpu", compute_type="int8")
print("model loaded", flush=True)

for wav in sorted(glob.glob(f"{W}/audio/*.wav")):
    base = os.path.splitext(os.path.basename(wav))[0]
    out = f"{W}/transcripts/{base}.json"
    if os.path.exists(out):
        print(f"skip {base}", flush=True)
        continue
    segs, info = model.transcribe(wav, word_timestamps=True, vad_filter=True)
    data = {"file": base, "language": info.language, "lang_prob": info.language_probability,
            "duration": info.duration, "segments": []}
    for s in segs:
        data["segments"].append({
            "start": round(s.start, 3), "end": round(s.end, 3),
            "text": s.text.strip(),
            "words": [{"w": w.word, "s": round(w.start, 3), "e": round(w.end, 3),
                       "p": round(w.probability, 3)} for w in (s.words or [])],
        })
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"OK {base}  lang={info.language} segs={len(data['segments'])}", flush=True)
print("DONE", flush=True)
