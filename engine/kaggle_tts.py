"""Run Qwen3-TTS on Kaggle's free GPU (2x T4) and bring the audio back.

    python3 kaggle_tts.py design voices/design.json voices/          # one-time: make the house voices
    python3 kaggle_tts.py clone jobs.json out_dir/                   # nightly: voice a batch of lines

jobs.json for clone: [{"id": "abc123", "voice": "af_bella", "text": "Hello there."}, ...]
Each job comes back as out_dir/<id>.wav (24 kHz mono). Voices are cloned from engine/voices/<voice>.wav
(fetched from the public repo on GitHub, so commit new voices before using them).

Needs the Kaggle API token in KAGGLE_API_TOKEN (or ~/.kaggle/access_token). Kaggle username: KAGGLE_USERNAME
(default vatsalthakkar1311). Exit code 0 = all jobs done; 2 = Kaggle unavailable / failed (caller falls back).
"""
import base64, json, os, shutil, subprocess, sys, tempfile, time, zipfile

USER = os.environ.get("KAGGLE_USERNAME", "vatsalthakkar1311").lower()
SLUG = os.environ.get("KAGGLE_TTS_SLUG", "snortlo-tts")
RAW = "https://raw.githubusercontent.com/vk1311/snortlo/main/engine/voices/"
MAX_WAIT = int(os.environ.get("KAGGLE_MAX_WAIT", "5400"))      # seconds to wait for a run

KERNEL = r'''
import base64, json, os, subprocess, sys, time, urllib.request, zipfile
t0 = time.time()
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--no-deps", "qwen-tts"], check=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "transformers==4.57.3", "accelerate==1.12.0",
                "onnxruntime", "librosa", "soundfile", "einops", "sox"], check=True)
import torch, soundfile as sf, numpy as np
from qwen_tts import Qwen3TTSModel
cfg = json.loads(base64.b64decode("__CFG__").decode())
os.makedirs("/kaggle/working/out", exist_ok=True)
log = {"ok": [], "failed": [], "setup_s": round(time.time() - t0)}
if cfg["mode"] == "design":
    m = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", device_map="cuda:0", dtype=torch.float16)
    for key, v in cfg["voices"].items():
        try:
            w, sr = m.generate_voice_design(text=cfg["ref_text"], language="English", instruct=v["instruct"])
            sf.write(f"/kaggle/working/out/{key}.wav", w[0], sr); log["ok"].append(key)
        except Exception as e:
            log["failed"].append([key, repr(e)[:300]])
else:
    m = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base", device_map="cuda:0", dtype=torch.float16)
    prompts = {}
    for v in sorted({j["voice"] for j in cfg["jobs"]}):
        p = f"/kaggle/working/{v}.wav"
        urllib.request.urlretrieve(cfg["raw"] + v + ".wav", p)
        prompts[v] = m.create_voice_clone_prompt(ref_audio=p, ref_text=cfg["ref_text"], x_vector_only_mode=False)
    by_voice = {}
    for j in cfg["jobs"]: by_voice.setdefault(j["voice"], []).append(j)
    for v, js in by_voice.items():
        for i in range(0, len(js), 8):                       # small batches keep T4 memory happy
            chunk = js[i:i + 8]
            try:
                ws, sr = m.generate_voice_clone(text=[j["text"] for j in chunk], language=["English"] * len(chunk),
                                                voice_clone_prompt=prompts[v])
                for j, w in zip(chunk, ws):
                    sf.write(f"/kaggle/working/out/{j['id']}.wav", w, sr); log["ok"].append(j["id"])
            except Exception as e:
                for j in chunk:
                    try:
                        w, sr = m.generate_voice_clone(text=j["text"], language="English", voice_clone_prompt=prompts[v])
                        sf.write(f"/kaggle/working/out/{j['id']}.wav", w[0], sr); log["ok"].append(j["id"])
                    except Exception as e2:
                        log["failed"].append([j["id"], repr(e2)[:300]])
log["total_s"] = round(time.time() - t0)
json.dump(log, open("/kaggle/working/out/_log.json", "w"))
with zipfile.ZipFile("/kaggle/working/tts_out.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in os.listdir("/kaggle/working/out"): z.write("/kaggle/working/out/" + f, f)
import shutil; shutil.rmtree("/kaggle/working/out")
print("DONE", json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in log.items()}))
'''


def kaggle(*args, timeout=600):
    r = subprocess.run(["kaggle", *args], capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr).strip()


def run(cfg, out_dir):
    """Push one GPU job, wait, download. Returns (ok, message)."""
    work = tempfile.mkdtemp(prefix="kgtts-")
    script = KERNEL.replace("__CFG__", base64.b64encode(json.dumps(cfg).encode()).decode())
    open(os.path.join(work, "run.py"), "w").write(script)
    json.dump({"id": f"{USER}/{SLUG}", "title": SLUG, "code_file": "run.py", "language": "python",
               "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
               "machine_shape": "NvidiaTeslaT4",
               "dataset_sources": [], "competition_sources": [], "kernel_sources": []},
              open(os.path.join(work, "kernel-metadata.json"), "w"))
    code, out = kaggle("kernels", "push", "-p", work)
    if code != 0 or "error" in out.lower() and "successfully" not in out.lower():
        return False, "push failed: " + out[-400:]
    t0, status = time.time(), ""
    while time.time() - t0 < MAX_WAIT:
        time.sleep(20)
        code, status = kaggle("kernels", "status", f"{USER}/{SLUG}")
        s = status.lower()
        if "complete" in s: break
        if "error" in s or "cancel" in s: return False, "run failed: " + status[-300:]
    else:
        return False, f"timed out after {MAX_WAIT}s ({status[-120:]})"
    dl = tempfile.mkdtemp(prefix="kgout-")
    code, out = kaggle("kernels", "output", f"{USER}/{SLUG}", "-p", dl, timeout=1800)
    zp = os.path.join(dl, "tts_out.zip")
    if not os.path.exists(zp):
        return False, "no output zip: " + out[-300:]
    os.makedirs(out_dir, exist_ok=True)
    with zipfile.ZipFile(zp) as z: z.extractall(out_dir)
    log = json.load(open(os.path.join(out_dir, "_log.json")))
    shutil.rmtree(work, ignore_errors=True); shutil.rmtree(dl, ignore_errors=True)
    if log["failed"] and not log["ok"]:
        return False, f"all jobs failed: {log['failed'][:2]}"
    return True, f"{len(log['ok'])} ok, {len(log['failed'])} failed, {log['total_s']}s on Kaggle"


if __name__ == "__main__":
    mode, src, out_dir = sys.argv[1:4]
    if mode == "design":
        d = json.load(open(src))
        cfg = {"mode": "design", "ref_text": d["ref_text"], "voices": d["voices"]}
    else:
        design = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices", "design.json")))
        cfg = {"mode": "clone", "ref_text": design["ref_text"], "raw": RAW, "jobs": json.load(open(src))}
    ok, msg = run(cfg, out_dir)
    print(("OK " if ok else "FAILED ") + msg)
    sys.exit(0 if ok else 2)
