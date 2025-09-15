# Page Table Simulator Project

## Overview
A single-level page table simulator with 4 KB pages (PAGE_OFFSET = 12). This tool reads memory traces and evaluates three page-replacement policies: random, LRU, and CLOCK.

> **Important**: Do not change `memsim.py` command-line arguments or the five final summary lines (grading scripts parse them). You may extend the MMU interface/implementation and adjust how `memsim.py` calls it internally.

## Table of Contents
- [Project Layout](#project-layout)
- [Requirements](#requirements)
- [Usage](#usage)
- [Input / Output Formats](#input--output-formats)
- [Replacement Policies](#replacement-policies)
- [MMU Responsibilities](#mmu-responsibilities)
- [Quick Examples](#quick-examples)
- [Testing & Baselines](#testing--baselines-short-traces)
- [Experiments for the Report](#experiments-for-the-report-large-traces)
- [Report Writing Guide](#report-writing-guide)
- [Troubleshooting / FAQ](#troubleshooting--faq)
- [Suggested .gitignore / .gitattributes](#suggested-gitignore--gitattributes)
- [Acknowledgments](#acknowledgments)

## Project Layout

```
OS-Assignment-2-main/
├─ memsim.py                  # main entry; parses trace & drives MMU
├─ mmu.py                     # MMU base class / interface
├─ lrummu.py                  # LRU implementation
├─ clockmmu.py                # CLOCK (Second-Chance) implementation
├─ randmmu.py                 # Random replacement
│
├─ trace1 / trace2 / trace3   # short traces (correctness/regression)
├─ swim.trace / bzip.trace / gcc.trace / sixpack.trace  # large traces (report)
│
├─ run_traces_v3.py           # optional: regression runner (.ans pairing)
├─ experiment_runner.py       # optional: sweep frames×algos×traces, plots
└─ README.md
```

## Requirements

- Python 3.10+ (3.12/3.13 recommended)
- Optional for plotting:
  ```bash
  python -m pip install matplotlib
  ```

## Usage

```bash
python memsim.py <trace_file> <num_frames> <replacement_mode> <mode>
```

| Argument | Description |
|----------|-------------|
| `trace_file` | Path to a trace file. Each non-empty line: `0x<hex_addr> R\|W` |
| `num_frames` | Integer ≥ 1 |
| `replacement_mode` | `rand` \| `lru` \| `clock` |
| `mode` | `quiet` (summary only) \| `debug` (per-event logs) |

## Input / Output Formats

**Trace line format:**
```
0x<hex_logical_address>  R|W
```

**Final summary (must be exactly these five lines):**
```
total memory frames: <int>
events in trace: <int>
total disk reads: <int>
total disk writes: <int>
page fault rate: <float>
```

## Replacement Policies

- **RAND** — Evict a uniformly random resident page (non-deterministic; average if analyzed).
- **LRU** — Evict the least recently used page (timestamps or ordered structure).
- **CLOCK (Second-Chance)** — Circular list with reference bit:
  - `reference==1` → set 0 & skip
  - `reference==0` → evict

> **Note**: An ESC variant also considers the dirty bit to prefer clean victims. This project uses clock, not ESC.

## MMU Responsibilities

- Compute page number: `page = logical_address >> 12` (4 KB pages)
- Track resident pages and per-page metadata:
  - Dirty bit: 0 when loaded; set to 1 on write access
  - Policy data (e.g., `last_used` for LRU; `reference` for CLOCK)
- On each access:
  - **Hit** → if write: dirty=1; update policy metadata
  - **Miss** → page_faults += 1; if no free frame, choose victim per policy; if victim dirty==1, disk_writes += 1; load new page (disk_reads += 1); mark dirty=1 for write, else 0

## Quick Examples

**Windows PowerShell:**
```powershell
py .\memsim.py .\trace1 4 lru quiet
py .\memsim.py .\swim.trace 64 clock quiet
```

**Linux / macOS:**
```bash
python memsim.py trace1 4 lru quiet
python memsim.py swim.trace 64 clock quiet
```

## Testing & Baselines (Short Traces)

Use `trace1`, `trace2`, `trace3` for fast correctness & regression.

```bash
# Generate/refresh *.ans baselines from current outputs
py .\run_traces_v3.py .\memsim.py --write-ans

# Later compare against baselines
py .\run_traces_v3.py .\memsim.py
```

The runner pairs `<base>-<frames>frames-<algo>.ans` with `<base>` or `<base>.trace` and compares the five summary fields.

## Experiments for the Report (Large Traces)

**Traces:** `swim.trace`, `bzip.trace`, `gcc.trace`, `sixpack.trace`

Sweep frames across small → near-demand → large (e.g., 4,8,16,32,64,128,256,512) with lru and clock (optionally rand, averaged).

**Metrics:**
- Page fault rate = page_faults / events
- Total disk reads (loads on miss)
- Total disk writes (dirty evictions)

**One-shot experiment & plots (optional):**
```bash
py .\experiment_runner.py --memsim .\memsim.py --frames 4,8,16,32,64,128,256,512 --algos lru,clock --traces swim.trace,bzip.trace,gcc.trace,sixpack.trace
```

Outputs to `results/`:
- `results.csv` (raw data)
- `*_pfr.png`, `*_reads.png`, `*_writes.png` (per-trace plots)
- `results.md` (index)

Without matplotlib, the tool still writes `results.csv` and skips plotting.

## Report Writing Guide

1. **Introduction** — Page replacement problem & intuition for rand/lru/clock and their trade-offs.
2. **Methods** — Frames range (shortage → near demand → excess), algorithms, metrics; how you detect the knee; whether rand is averaged.
3. **Results** — For each trace, include plots (fault-rate / reads / writes vs frames) and brief analysis:
   - Which algorithm wins at small memory?
   - Where is the knee (approx memory demand)?
   - Any anomalies (e.g., spikes in writes from dirty evictions)?
4. **Conclusions** — 2–3 takeaways (e.g., LRU often best at small frames; CLOCK close with lower overhead; no single policy dominates; estimated demand ranges per trace).

## Troubleshooting / FAQ

- **ValueError: invalid literal for int() with base 16: 'total'** → You passed an .ans file instead of a trace. Real traces start with `0x... R|W`.
- **PowerShell multiline** → Use a backtick `` ` `` at end of line (no trailing spaces). In CMD, use `^`.
- **Encoding/garbled output (PowerShell):**
  ```powershell
  $OutputEncoding = [Console]::OutputEncoding = [Text.UTF8Encoding]::UTF8
  ```
- **__pycache__** → Ignore or delete; Python regenerates it automatically.

## Suggested .gitignore / .gitattributes

**.gitignore**
```
# bytecode/cache
__pycache__/
*.py[cod]
*$py.class

# generated outputs
results/

# baselines (optional: keep if you want regression in repo)
# *.ans

# large traces (optional: avoid bloating the repo)
# *.trace
# trace1
# trace2
# trace3
```

**.gitattributes**
```
* text=auto
*.py    text eol=lf
*.md    text eol=lf
*.ans   text eol=lf
*.trace text eol=lf
*.csv   text eol=lf
*.png   binary
*.jpg   binary
*.pdf   binary
```

## Acknowledgments

Course assignment on virtual memory and page replacement (see textbook paging/replacement chapter for background).