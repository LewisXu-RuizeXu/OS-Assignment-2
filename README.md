Virtual Memory Page Replacement Simulator (4 KB pages)

This project implements a single-level page-table simulator with a fixed page size of 4 KB (PAGE_OFFSET = 12). The program reads a memory trace (logical address + access type), simulates page hits/misses under a chosen replacement policy, and reports page-fault rate and simulated disk I/O.

Important:

Do not change memsim.py’s command-line arguments or the five final summary lines (grading scripts parse them).

You may modify/extend the MMU implementation and its interface (mmu.py, lrummu.py, clockmmu.py, randmmu.py), and you may change how memsim.py calls the MMU internally.

Project Structure 
OS-Assignment-2-main/
├─ memsim.py
├─ mmu.py
├─ lrummu.py
├─ clockmmu.py
├─ randmmu.py
├─ trace1 / trace2 / trace3                  # short traces (correctness/regression)
├─ swim.trace / bzip.trace / gcc.trace / sixpack.trace  # large traces (report)
├─ *.ans                                     # optional: expected/baseline outputs
├─ run_traces_v3.py                          # optional: regression runner
├─ experiment_runner.py                      # optional: experiment & plotting tool
└─ README.md

Requirements

Python 3.10+ (3.12/3.13 recommended)

Optional for plots: matplotlib

python -m pip install matplotlib

Usage
python memsim.py <trace_file> <num_frames> <replacement_mode> <mode>


<trace_file>: path to a text trace. Each non-empty line:

0x<hex_logical_address>  R|W


<num_frames>: integer ≥ 1

<replacement_mode>: rand | lru | clock

<mode>:

quiet — no output until the end (for grading/experiments)

debug — per-event logs to help development

Required final summary (exactly these five lines)
total memory frames: <int>
events in trace: <int>
total disk reads: <int>
total disk writes: <int>
page fault rate: <float>

Examples

Windows PowerShell

py .\memsim.py .\trace1 4 lru quiet
py .\memsim.py .\swim.trace 64 clock quiet


Linux / macOS

python memsim.py trace1 4 lru quiet
python memsim.py swim.trace 64 clock quiet

What the MMU Must Do

Page number: page = logical_address >> 12

Resident set & metadata: choose suitable structures (e.g., dicts/lists). For each resident page keep:

dirty (modified bit): 0 when loaded; set to 1 on a write access.

Policy info (e.g., last_used timestamp for LRU; reference bit for CLOCK).

On each access:

If hit:

On write: dirty = 1.

Update policy metadata (recency/reference).

If miss:

page_faults += 1

If a free frame exists, use it; else choose a victim per policy.

If victim dirty == 1, then disk_writes += 1 (simulate write-back).

Load new page: disk_reads += 1; mark dirty = 1 for write access, otherwise 0.

You can add helper methods/state to the MMU and adjust how memsim.py invokes it. Keep the summary output unchanged.

Replacement Policies

RAND — evict a uniformly random resident page (non-deterministic; average over multiple runs if used in analysis).

LRU — evict the least recently used page (e.g., timestamps or ordered structure).

CLOCK (Second-Chance) — circular list of frames with a reference bit:

If reference == 1, set it to 0 and skip (second chance).

If reference == 0, evict that frame.

(Note: An “ESC” enhanced variant also considers the dirty bit to prefer clean victims. This project uses clock, not ESC.)

Debugging & Regression (short traces)

Use trace1, trace2, trace3 for fast correctness checks and readable debug logs.
Optional helper: run_traces_v3.py

# Compare against existing *.ans baselines (auto-pairs "<base>-<frames>frames-<algo>.ans" with "<base>" or "<base>.trace")
py .\run_traces_v3.py .\memsim.py

# Generate/refresh all *.ans baselines from current outputs
py .\run_traces_v3.py .\memsim.py --write-ans

Performance Study for the Report (large traces)

Use swim.trace, bzip.trace, gcc.trace, sixpack.trace across a range of frame counts (e.g., 4,8,16,32,64,128,256,512) and at least the algorithms lru and clock (optionally rand, average multiple runs).

Metrics

Page fault rate = page_faults / events

Total disk reads (loads on misses)

Total disk writes (write-backs of dirty victims)

Estimating “memory needed”

Look for the knee in the fault-rate vs frames curve (further increases in frames yield small marginal gains).

One-shot experiment & plots (optional)

Helper: experiment_runner.py. It sweeps frames×algos×traces, writes results/results.csv, and (if matplotlib is installed) plots:

*_pfr.png — fault rate vs frames

*_writes.png — disk writes vs frames

*_reads.png — disk reads vs frames

py .\experiment_runner.py --memsim .\memsim.py --frames 4,8,16,32,64,128,256,512 --algos lru,clock --traces swim.trace,bzip.trace,gcc.trace,sixpack.trace


(Without matplotlib it still writes the CSV and skips plots.)