#!/usr/bin/env python3
"""Prepara um vídeo para o Claude "assistir": baixa, extrai quadros e transcreve.

Uso:
    python3 watch.py <url-ou-arquivo> [--out DIR] [--max-frames N] [--interval SEG]
                     [--width PX] [--lang pt] [--model small] [--no-transcript]

Saída (em --out):
    video.*            vídeo original (se veio de URL)
    frames/0001_00m05s.jpg ...   quadros com o timestamp no nome
    transcript.txt     transcrição com timestamps [mm:ss]
    manifest.json      metadados, lista de quadros e segmentos
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile


def log(msg):
    print(f"[watch] {msg}", file=sys.stderr, flush=True)


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, capture_output=True, **kw)


def fmt(t):
    t = int(round(t))
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def fname_time(t):
    t = int(round(t))
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h{m:02d}m{s:02d}s" if h else f"{m:02d}m{s:02d}s"


def is_url(s):
    return re.match(r"^https?://", s) is not None


def download(url, out):
    if not shutil.which("yt-dlp"):
        sys.exit("yt-dlp não encontrado. Instale com: pip install yt-dlp")
    log(f"baixando {url}")
    tpl = os.path.join(out, "video.%(ext)s")
    cmd = [
        "yt-dlp", "--no-playlist", "-f", "bv*[height<=720]+ba/b[height<=720]/b",
        "--merge-output-format", "mp4", "-o", tpl,
        "--write-subs", "--write-auto-subs", "--sub-langs", "pt.*,en.*,.*-orig",
        "--sub-format", "vtt", "--convert-subs", "vtt",
        "--write-info-json", url,
    ]
    try:
        run(cmd)
    except subprocess.CalledProcessError:
        # Legendas às vezes falham (rate limit); tenta só o vídeo.
        log("falha com legendas, tentando apenas o vídeo")
        run(cmd[:8] + ["--write-info-json", url])
    vids = [p for p in glob.glob(os.path.join(out, "video.*"))
            if p.rsplit(".", 1)[-1] in ("mp4", "mkv", "webm", "mov", "m4a", "mp3")]
    if not vids:
        sys.exit("download não produziu arquivo de vídeo")
    info = {}
    ij = os.path.join(out, "video.info.json")
    if os.path.exists(ij):
        with open(ij) as f:
            raw = json.load(f)
        info = {k: raw.get(k) for k in
                ("title", "uploader", "upload_date", "duration", "webpage_url", "description")}
        os.remove(ij)
    return vids[0], info


def probe(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
             "-of", "json", path])
    d = json.loads(r.stdout)
    dur = float(d.get("format", {}).get("duration") or 0)
    types = {s.get("codec_type") for s in d.get("streams", [])}
    return dur, "video" in types, "audio" in types


def extract_frames(video, out, duration, max_frames, interval, width):
    fdir = os.path.join(out, "frames")
    os.makedirs(fdir, exist_ok=True)
    if interval is None:
        # Distribui max_frames uniformemente; no mínimo 1s entre quadros.
        interval = max(1.0, duration / max_frames) if duration else 2.0
    n = min(max_frames, max(1, int(duration // interval) + 1)) if duration else max_frames
    log(f"extraindo até {n} quadros (1 a cada {interval:.1f}s)")
    frames = []
    for i in range(n):
        t = min(i * interval + interval / 2, max(duration - 0.1, 0))
        name = f"{i + 1:04d}_{fname_time(t)}.jpg"
        path = os.path.join(fdir, name)
        try:
            run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", video,
                 "-frames:v", "1", "-vf", f"scale='min({width},iw)':-2", "-q:v", "4", path])
        except subprocess.CalledProcessError:
            continue
        if os.path.exists(path):
            frames.append({"time": round(t, 2), "timestamp": fmt(t), "file": os.path.relpath(path, out)})
    return frames


def parse_vtt(path):
    segs, seen = [], set()
    ts = re.compile(r"(\d+):(\d+):(\d+)[.,](\d+)\s*-->|(\d+):(\d+)[.,](\d+)\s*-->")
    cur = None
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            m = ts.search(line)
            if m:
                if m.group(1):
                    cur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
                else:
                    cur = int(m.group(5)) * 60 + int(m.group(6))
                continue
            if not line or cur is None or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
                continue
            text = re.sub(r"<[^>]+>", "", line).strip()
            if text and text not in seen:  # legendas automáticas repetem linhas
                seen.add(text)
                segs.append({"start": cur, "text": text})
    return segs


def transcribe(video, out, lang, model_name):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        log("faster-whisper não instalado (pip install faster-whisper); pulando transcrição")
        return None, None
    log(f"transcrevendo com whisper '{model_name}' (pode demorar)")
    wav = os.path.join(tempfile.mkdtemp(), "audio.wav")
    run(["ffmpeg", "-y", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", "16000", wav])
    model = WhisperModel(model_name, device="auto", compute_type="int8")
    segments, info = model.transcribe(wav, language=lang, vad_filter=True)
    segs = [{"start": round(s.start, 2), "text": s.text.strip()} for s in segments]
    shutil.rmtree(os.path.dirname(wav), ignore_errors=True)
    return segs, info.language


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="URL (YouTube, Instagram, TikTok...) ou caminho de arquivo")
    ap.add_argument("--out", default=None, help="pasta de saída (padrão: ./watch_<nome>)")
    ap.add_argument("--max-frames", type=int, default=30)
    ap.add_argument("--interval", type=float, default=None, help="segundos entre quadros")
    ap.add_argument("--width", type=int, default=768)
    ap.add_argument("--lang", default=None, help="idioma do áudio (ex.: pt, en); padrão: detectar")
    ap.add_argument("--model", default="small", help="modelo whisper: tiny, base, small, medium, large-v3")
    ap.add_argument("--no-transcript", action="store_true")
    a = ap.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} não encontrado. Instale o ffmpeg.")

    base = re.sub(r"[^\w-]+", "_", os.path.basename(a.source.rstrip("/")))[:40] or "video"
    out = os.path.abspath(a.out or f"watch_{base}")
    os.makedirs(out, exist_ok=True)

    info = {}
    if is_url(a.source):
        video, info = download(a.source, out)
    else:
        video = os.path.abspath(a.source)
        if not os.path.exists(video):
            sys.exit(f"arquivo não encontrado: {video}")

    duration, has_video, has_audio = probe(video)
    log(f"duração {fmt(duration)}, vídeo={has_video}, áudio={has_audio}")

    frames = extract_frames(video, out, duration, a.max_frames, a.interval, a.width) if has_video else []

    segs, source, lang = None, None, a.lang
    subs = sorted(glob.glob(os.path.join(out, "video*.vtt")))
    if subs and not a.no_transcript:
        segs, source = parse_vtt(subs[0]), "legendas: " + os.path.basename(subs[0])
    if not segs and has_audio and not a.no_transcript:
        try:
            segs, lang = transcribe(video, out, a.lang, a.model)
        except Exception as e:  # rede bloqueada, modelo ausente etc.
            log(f"transcrição falhou ({type(e).__name__}: {str(e)[:120]}); seguindo só com quadros")
            segs = None
        source = "whisper" if segs is not None else None

    if segs:
        with open(os.path.join(out, "transcript.txt"), "w", encoding="utf-8") as f:
            for s in segs:
                f.write(f"[{fmt(s['start'])}] {s['text']}\n")

    manifest = {
        "source": a.source, "video_file": video, "duration": round(duration, 2),
        "duration_hms": fmt(duration), "info": info, "transcript_source": source,
        "language": lang, "frames": frames, "transcript": segs or [],
    }
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "out_dir": out, "duration": fmt(duration), "title": info.get("title"),
        "frames": len(frames), "frames_dir": os.path.join(out, "frames"),
        "transcript": os.path.join(out, "transcript.txt") if segs else None,
        "transcript_source": source,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
