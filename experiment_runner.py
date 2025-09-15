#!/usr/bin/env python3
"""
Experiment runner for the VM replacement simulator.

Usage examples (Windows PowerShell):
  py .\experiment_runner.py --memsim .\memsim.py
  py .\experiment_runner.py --memsim .\memsim.py --frames 4,8,16,32,64,128,256 --algos lru,clock --traces swim.trace,bzip.trace,gcc.trace,sixpack.trace
  py .\experiment_runner.py --memsim .\memsim.py --python python  # specify the interpreter used to run memsim.py
"""
import argparse
import csv
import math
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_TRACES = ["swim.trace", "bzip.trace", "gcc.trace", "sixpack.trace"]
DEFAULT_FRAMES = [4, 8, 16, 32, 64, 128, 256, 512]
DEFAULT_ALGOS  = ["lru", "clock"]  # add "rand" if you want; results will vary run-to-run
RAND_REPEATS   = 3  # how many times to repeat rand and average

STATS_FIELDS = ["frames", "events", "reads", "writes", "rate"]

_stats_re = re.compile(
    r"total memory frames:\s*(?P<frames>\d+)\s*"
    r"events in trace:\s*(?P<events>\d+)\s*"
    r"total disk reads:\s*(?P<reads>\d+)\s*"
    r"total disk writes:\s*(?P<writes>\d+)\s*"
    r"page fault rate:\s*(?P<rate>[\d.]+)\s*",
    re.IGNORECASE | re.DOTALL
)

def parse_stats(text: str):
    m = _stats_re.search(text)
    if m:
        d = m.groupdict()
        return {
            "frames": int(d["frames"]),
            "events": int(d["events"]),
            "reads": int(d["reads"]),
            "writes": int(d["writes"]),
            "rate": float(d["rate"]),
        }
    # tolerant line-by-line parsing
    vals = {"frames": None, "events": None, "reads": None, "writes": None, "rate": None}
    for line in text.splitlines():
        low = line.strip().lower()
        if low.startswith("total memory frames:"):
            vals["frames"] = int(re.findall(r"\d+", line)[0])
        elif low.startswith("events in trace:"):
            vals["events"] = int(re.findall(r"\d+", line)[0])
        elif low.startswith("total disk reads:"):
            vals["reads"] = int(re.findall(r"\d+", line)[0])
        elif low.startswith("total disk writes:"):
            vals["writes"] = int(re.findall(r"\d+", line)[0])
        elif low.startswith("page fault rate:"):
            vals["rate"] = float(re.findall(r"[0-9.]+", line)[0])
    if any(v is None for v in vals.values()):
        raise ValueError("Could not parse stats from memsim output.")
    return vals

def run_once(pyexe: str, memsim: Path, trace: Path, frames: int, algo: str):
    proc = subprocess.run(
        [pyexe, str(memsim), str(trace), str(frames), algo, "quiet"],
        capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise RuntimeError(f"memsim.py failed (frames={frames}, algo={algo}, trace={trace.name}):\n{proc.stderr}")
    return parse_stats(proc.stdout)

def ensure_traces(traces):
    ok = []
    for t in traces:
        p = Path(t)
        if not p.exists():
            # also try bare name without .trace
            p2 = Path(t + ".trace")
            if p2.exists():
                p = p2
            else:
                print(f"[WARN] Trace not found: {t} (skipped)")
                continue
        ok.append(p)
    return ok

def main(argv=None):
    ap = argparse.ArgumentParser(description="Run VM replacement experiments and plot results.")
    ap.add_argument("--memsim", required=True, help="Path to memsim.py")
    ap.add_argument("--python", default=sys.executable, help="Python interpreter to run memsim.py")
    ap.add_argument("--traces", default=",".join(DEFAULT_TRACES), help="Comma-separated trace filenames")
    ap.add_argument("--frames", default=",".join(map(str, DEFAULT_FRAMES)), help="Comma-separated frame counts")
    ap.add_argument("--algos",  default=",".join(DEFAULT_ALGOS),  help="Comma-separated algos: lru,clock,rand")
    ap.add_argument("--outdir", default="results", help="Directory to write CSV and plots")
    args = ap.parse_args(argv)

    memsim = Path(args.memsim).resolve()
    if not memsim.exists():
        ap.error(f"memsim.py not found: {memsim}")

    traces = [s.strip() for s in args.traces.split(",") if s.strip()]
    frames = [int(x) for x in args.frames.split(",") if x.strip()]
    algos  = [s.strip() for s in args.algos.split(",") if s.strip()]

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    trace_paths = ensure_traces(traces)
    if not trace_paths:
        ap.error("No valid traces found.")

    rows = []
    for trace in trace_paths:
        for algo in algos:
            if algo == "rand":
                # run multiple times and average
                agg = {"frames": None, "events": None, "reads": [], "writes": [], "rate": []}
                for f in frames:
                    reps = []
                    for _ in range(RAND_REPEATS):
                        r = run_once(args.python, memsim, trace, f, algo)
                        reps.append(r)
                    # average reads/writes/rate; keep frames/events from first
                    avg_reads  = sum(x["reads"] for x in reps) / len(reps)
                    avg_writes = sum(x["writes"] for x in reps) / len(reps)
                    avg_rate   = sum(x["rate"] for x in reps) / len(reps)
                    rows.append({
                        "trace": trace.name,
                        "algo": algo,
                        "frames": f,
                        "events": reps[0]["events"],
                        "reads": avg_reads,
                        "writes": avg_writes,
                        "rate": avg_rate,
                        "repeats": len(reps)
                    })
            else:
                for f in frames:
                    r = run_once(args.python, memsim, trace, f, algo)
                    rows.append({
                        "trace": trace.name,
                        "algo": algo,
                        "frames": f,
                        "events": r["events"],
                        "reads": r["reads"],
                        "writes": r["writes"],
                        "rate": r["rate"],
                        "repeats": 1
                    })

    # write CSV
    csv_path = outdir / "results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        w = csv.DictWriter(fp, fieldnames=["trace","algo","frames","events","reads","writes","rate","repeats"])
        w.writeheader()
        w.writerows(rows)
    print(f"[OK] Wrote {csv_path}")

    # plots
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("[WARN] matplotlib not installed; skipping plots.")
        return 0

    # Per-trace plots: page-fault rate vs frames (log2 x), one plot per trace
    from collections import defaultdict
    by_trace = defaultdict(list)
    for row in rows:
        by_trace[row["trace"]].append(row)

    for trace_name, data in by_trace.items():
        # sort by frames
        data.sort(key=lambda r: (r["algo"], r["frames"]))
        # 1) page fault rate
        plt.figure()
        algos_present = sorted({r["algo"] for r in data})
        for algo in algos_present:
            xs = [r["frames"] for r in data if r["algo"] == algo]
            ys = [r["rate"]   for r in data if r["algo"] == algo]
            plt.plot(xs, ys, marker="o", label=algo)
        plt.xscale("log", base=2)
        plt.xlabel("Frames (log2)")
        plt.ylabel("Page fault rate")
        plt.title(f"{trace_name} — Page Fault Rate vs Frames")
        plt.legend()
        plt.grid(True, which="both", linestyle="--", alpha=0.4)
        fig1 = outdir / f"{trace_name}_pfr.png"
        plt.savefig(fig1, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"[OK] Wrote {fig1}")

        # 2) disk writes
        plt.figure()
        for algo in algos_present:
            xs = [r["frames"] for r in data if r["algo"] == algo]
            ys = [r["writes"] for r in data if r["algo"] == algo]
            plt.plot(xs, ys, marker="o", label=algo)
        plt.xscale("log", base=2)
        plt.xlabel("Frames (log2)")
        plt.ylabel("Total disk writes")
        plt.title(f"{trace_name} — Disk Writes vs Frames")
        plt.legend()
        plt.grid(True, which="both", linestyle="--", alpha=0.4)
        fig2 = outdir / f"{trace_name}_writes.png"
        plt.savefig(fig2, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"[OK] Wrote {fig2}")

        # 3) disk reads
        plt.figure()
        for algo in algos_present:
            xs = [r["frames"] for r in data if r["algo"] == algo]
            ys = [r["reads"]  for r in data if r["algo"] == algo]
            plt.plot(xs, ys, marker="o", label=algo)
        plt.xscale("log", base=2)
        plt.xlabel("Frames (log2)")
        plt.ylabel("Total disk reads")
        plt.title(f"{trace_name} — Disk Reads vs Frames")
        plt.legend()
        plt.grid(True, which="both", linestyle="--", alpha=0.4)
        fig3 = outdir / f"{trace_name}_reads.png"
        plt.savefig(fig3, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"[OK] Wrote {fig3}")

    # Simple README stub
    md = outdir / "results.md"
    with md.open("w", encoding="utf-8") as fp:
        fp.write("# Simulator Results (Auto-generated)\n\n")
        fp.write(f"- memsim: `{memsim}`\n")
        fp.write(f"- traces: {', '.join([p.name for p in trace_paths])}\n")
        fp.write(f"- frames: {', '.join(map(str, frames))}\n")
        fp.write(f"- algos: {', '.join(algos)}\n\n")
        fp.write("## Plots\n\n")
        for trace_name in by_trace.keys():
            fp.write(f"### {trace_name}\n\n")
            fp.write(f"![PFR](./{trace_name}_pfr.png)\n\n")
            fp.write(f"![Writes](./{trace_name}_writes.png)\n\n")
            fp.write(f"![Reads](./{trace_name}_reads.png)\n\n")
    print(f"[OK] Wrote {md}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
