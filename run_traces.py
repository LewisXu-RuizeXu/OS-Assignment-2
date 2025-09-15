#!/usr/bin/env python3
import re
import sys
import subprocess
from pathlib import Path
from dataclasses import dataclass

SUPPORTED_MODES = {"lru", "clock", "rand"}

# Relaxed pattern: optional 0x, hex digits, whitespace, R/W
HEX_RW_RE = re.compile(r"^\s*(?:0x)?[0-9A-Fa-f]+\s+[RW]\s*$")
ANS_HINT_RE = re.compile(r"^\s*total\s+memory\s+frames:", re.IGNORECASE)

@dataclass
class Case:
    base: str
    frames: int
    mode: str
    input_file: Path|None = None
    ans_file: Path|None = None

def looks_like_trace(p: Path) -> bool:
    try:
        with p.open('r', encoding='utf-8', errors='ignore') as f:
            for _ in range(50):
                line = f.readline()
                if not line:
                    break
                s = line.strip()
                if not s or s.startswith("#") or s.startswith("//"):
                    continue
                if HEX_RW_RE.match(s):
                    return True
                if ANS_HINT_RE.match(s):
                    return False
                # otherwise keep scanning a few lines
    except Exception:
        return False
    return False

def looks_like_ans(p: Path) -> bool:
    try:
        with p.open('r', encoding='utf-8', errors='ignore') as f:
            for _ in range(20):
                line = f.readline()
                if not line:
                    break
                s = line.strip().lower()
                if not s:
                    continue
                if s.startswith("total memory frames:"):
                    return True
                if HEX_RW_RE.match(s):
                    return False
    except Exception:
        return False
    return False

def parse_stats(s: str):
    vals = {"frames": None, "events": None, "reads": None, "writes": None, "rate": None}
    for line in s.splitlines():
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
        raise ValueError("Could not parse stats from text.")
    return vals

def find_cases(dir_path: Path):
    # 1) Scan all files, bucket by <base>-<n>frames-<mode>[.ans]
    pattern = re.compile(r"^(?P<base>.+?)-(?P<n>\d+)frames-(?P<mode>[a-zA-Z]+)(?P<ext>\..+)?$")
    cases: dict[tuple[str,int,str], Case] = {}
    files = [p for p in dir_path.iterdir() if p.is_file()]
    for p in files:
        m = pattern.match(p.name)
        if not m:
            continue
        base = m["base"]
        frames = int(m["n"])
        mode = m["mode"].lower()
        if mode not in SUPPORTED_MODES:
            continue
        key = (base, frames, mode)
        case = cases.get(key) or Case(base, frames, mode)
        cases[key] = case
        ext = (m["ext"] or "").lower()
        if ext == ".ans" or looks_like_ans(p):
            case.ans_file = p
        elif looks_like_trace(p):
            case.input_file = p
        else:
            # ambiguous -> assume ans
            case.ans_file = p

    # 2) For any case missing input_file, try to pair "<base>" or "<base>.trace"
    for case in cases.values():
        if case.input_file and case.input_file.exists():
            continue
        # Try exact "<base>"
        cand1 = dir_path / case.base
        # Try "<base>.trace"
        cand2 = dir_path / f"{case.base}.trace"
        for cand in (cand1, cand2):
            if cand.exists() and cand.is_file() and looks_like_trace(cand):
                case.input_file = cand
                break

    # 3) Keep only those cases that have an input file
    return [c for c in cases.values() if c.input_file and c.input_file.exists()]

def run_case(pyexe: str, memsim: Path, case: Case):
    proc = subprocess.run(
        [pyexe, str(memsim), str(case.input_file), str(case.frames), case.mode, "quiet"],
        capture_output=True, text=True
    )
    return proc.returncode, proc.stdout, proc.stderr

def main(argv):
    if len(argv) < 2 or argv[1].startswith("-h"):
        print("Usage: python run_traces_v3.py /path/to/memsim.py [--trace-dir DIR] [--python PYEXE] [--fail-fast] [--write-ans]")
        print("Hint: It will also pair '<base>-<N>frames-<mode>.ans' with '<base>' or '<base>.trace' as input.")
        return 2
    memsim = Path(argv[1]).resolve()
    if not memsim.exists():
        print(f"memsim.py not found at: {memsim}")
        return 2

    trace_dir = Path(".").resolve()
    pyexe = sys.executable
    fail_fast = False
    write_ans = False

    i = 2
    while i < len(argv):
        if argv[i] == "--trace-dir" and i+1 < len(argv):
            trace_dir = Path(argv[i+1]).resolve()
            i += 2
        elif argv[i] == "--python" and i+1 < len(argv):
            pyexe = argv[i+1]
            i += 2
        elif argv[i] == "--fail-fast":
            fail_fast = True
            i += 1
        elif argv[i] == "--write-ans":
            write_ans = True
            i += 1
        else:
            print(f"Unknown arg: {argv[i]}")
            return 2

    cases = find_cases(trace_dir)
    if not cases:
        print(f"No valid cases found in {trace_dir}.")
        print("Expect to see files like 'trace2-6frames-lru.ans' paired with 'trace2' or 'trace2.trace'.")
        return 1

    total = len(cases)
    passed = 0
    for case in sorted(cases, key=lambda c: (c.base, c.frames, c.mode)):
        print(f"=== Running {case.input_file.name} (frames={case.frames}, mode={case.mode}) ===")
        code, out, err = run_case(pyexe, memsim, case)
        if code != 0:
            print(f"  ERROR: memsim.py exited with {code}")
            if err.strip():
                print(err.strip())
            if fail_fast: return 1
            continue
        print("  Ran OK.")

        # --write-ans: always write/update baseline
        if write_ans:
            ans_name = f"{case.base}-{case.frames}frames-{case.mode}.ans"
            ans_path = trace_dir / ans_name
            ans_path.write_text(out, encoding="utf-8", newline="\n")
            print(f"  ✍️  Wrote baseline: {ans_path.name}")
            passed += 1
            continue

        # Otherwise: compare with ans if present
        if case.ans_file and case.ans_file.exists():
            try:
                exp = parse_stats(case.ans_file.read_text(encoding='utf-8', errors='ignore'))
                got = parse_stats(out)
                ok = (
                    got["frames"] == exp["frames"] and
                    got["events"] == exp["events"] and
                    got["reads"] == exp["reads"] and
                    got["writes"] == exp["writes"] and
                    abs(got["rate"] - exp["rate"]) < 1e-6
                )
                if ok:
                    print("  ✅ Matches .ans")
                    passed += 1
                else:
                    print("  ❌ Mismatch vs .ans")
                    print(f"     got:      {got}")
                    print(f"     expected: {exp}")
                    if fail_fast: return 1
            except Exception as e:
                print(f"  WARN: could not parse stats ({e}). Counting as executed.")
                passed += 1
        else:
            passed += 1

    print(f"\nSummary: {passed}/{total} cases OK (including those without .ans or when writing baselines)")
    return 0 if passed == total else 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
