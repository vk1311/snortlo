"""Weekly long-form compilation: the week's animated stories (their full cuts) joined into one landscape video.
Usage: python3 engine/compile.py "<video title>" out.mp4 media/a-full.mp4 "Story title A" media/b-full.mp4 "Story title B" ...
Writes out.mp4 (1280x720, under GitHub's 100 MB limit), out.chapters.txt and out-thumb.png.
"""
import os, subprocess, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import cairocffi as cairo, anim as A

W, H = 1280, 720

def card(text, sub, path, w=W, h=H):
    s = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h); c = cairo.Context(s)
    c.set_source_rgb(*A.hexc("#FFD23F")); c.paint()
    A.text(c, sub, w / 2, h * 0.36, 34 * w / 1280, (0.1, 0.1, 0.13))
    c.select_font_face(A.FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); c.set_font_size(76)
    sc = min(1, (w - 120) / c.text_extents(text)[4]); A.text(c, text, w / 2, h * 0.52, 76 * sc * w / 1280, (0.06, 0.05, 0.09))
    A.text(c, "Snortlo", w / 2, h * 0.86, 30 * w / 1280, (0.1, 0.1, 0.13)); s.write_to_png(path)

def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True).stdout)

def main():
    title, out = sys.argv[1], sys.argv[2]; pairs = list(zip(sys.argv[3::2], sys.argv[4::2]))
    work = out + ".work"; os.makedirs(work, exist_ok=True); parts, chapters, t = [], [], 0.0
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", os.environ.get("CRF", "27"), "-pix_fmt", "yuv420p", "-r", "30",
           "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2"]
    for i, (vid, name) in enumerate(pairs):
        png = f"{work}/card{i}.png"; card(name, f"Story {i + 1}", png)
        cv = f"{work}/c{i}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", "2.5", "-i", png, "-f", "lavfi", "-t", "2.5", "-i", "anullsrc=r=48000:cl=stereo",
                        "-vf", f"scale={W}:{H},fade=t=in:d=0.3,fade=t=out:st=2.1:d=0.4", *enc, "-shortest", cv], check=True)
        sv = f"{work}/s{i}.mp4"   # vertical story centred on a blurred copy of itself
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vid, "-filter_complex",
                        f"[0:v]split[a][b];[b]scale={W}:-2,crop={W}:{H},gblur=sigma=30,eq=brightness=-0.2[bg];[a]scale=-2:{H}[fg];[bg][fg]overlay=(W-w)/2:0[v]",
                        "-map", "[v]", "-map", "0:a", *enc, sv], check=True)
        chapters.append((t, name)); t += 2.5 + dur(sv); parts += [cv, sv]
    lst = f"{work}/list.txt"; open(lst, "w").write("".join(f"file '{os.path.abspath(p)}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", out], check=True)
    fmt = lambda x: f"{int(x // 60)}:{int(x % 60):02d}" if x < 3600 else f"{int(x // 3600)}:{int(x % 3600 // 60):02d}:{int(x % 60):02d}"
    open(out.rsplit(".", 1)[0] + ".chapters.txt", "w").write("\n".join(f"{fmt(a)} {n}" for a, n in chapters) + "\n")
    card(title, f"{len(pairs)} stories · {int(t // 60)} min", out.rsplit(".", 1)[0] + "-thumb.png")
    subprocess.run(["rm", "-rf", work])
    mb = os.path.getsize(out) / 1048576; print(f"done {out} {t / 60:.1f} min {mb:.0f} MB")
    if mb > 95: print("WARNING: over GitHub's limit; re-run with CRF=30")

if __name__ == "__main__": main()
