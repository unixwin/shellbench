#!/bin/bash
# Gap-table v1 orchestration (one-shot, used for the inaugural run).
#
# Discipline: this box is shared with other build clusters.
#   - release build of rubash starts only at load<7 && MemAvailable>1.5G
#   - benchmark collection starts only at load<2 with no cargo/rustc
#     process alive, confirmed by two checks 30 s apart
# Everything is logged; a DONE marker file appears when finished.
set -u
ROOT="$HOME/workspace/shellbench"
WORK="$HOME/workspace/shellbench-build"
GNU="$HOME/workspace/rubash-audit/gnu-bash-5.3.20/bin/bash"
SRC="$HOME/workspace/rubash-fix4/clusters/sig/rubash"
SHA=1e72c7f9
LOG="$WORK/gap-v1.log"
mkdir -p "$WORK"
exec >>"$LOG" 2>&1
echo "=== run_gap_v1 start $(date -Is) ==="

load1() { awk '{print $1}' /proc/loadavg; }
memavail() { awk '/MemAvailable/{print $2}' /proc/meminfo; }
cargo_alive() { pgrep -x cargo >/dev/null || pgrep -x rustc >/dev/null; }

# ---- phase 1: release build ------------------------------------------------
while :; do
  ok=$(awk -v l="$(load1)" -v m="$(memavail)" 'BEGIN{print (l<7 && m>1572864)?1:0}')
  [ "$ok" = 1 ] && break
  sleep 30
done
echo "build window open $(date -Is) load=$(load1)"
if [ ! -x "$WORK/rubash/target/release/rubash" ]; then
  [ -d "$WORK/rubash" ] || git clone -q "$SRC" "$WORK/rubash"
  git -C "$WORK/rubash" checkout -q "$SHA"
  export PATH="$HOME/.cargo/bin:$PATH"
  export RUSTFLAGS="-C debuginfo=0" CARGO_BUILD_JOBS=2 CARGO_INCREMENTAL=0
  (cd "$WORK/rubash" && cargo build --release --locked) || {
    echo "BUILD FAILED"; echo FAIL > "$WORK/gap-v1.done"; exit 1; }
fi
RUBASH="$WORK/rubash/target/release/rubash"
echo "rubash sha: $(git -C "$WORK/rubash" rev-parse HEAD)"
echo "rubash bin: $RUBASH"
"$RUBASH" --version | head -1
"$GNU" --version | head -1

# ---- phase 2: quiet window for measurement ---------------------------------
while :; do
  if ! cargo_alive && awk -v l="$(load1)" 'BEGIN{exit !(l<2)}'; then
    sleep 30
    if ! cargo_alive && awk -v l="$(load1)" 'BEGIN{exit !(l<2)}'; then
      break
    fi
  fi
  sleep 30
done
echo "bench window open $(date -Is) load=$(load1)"

cd "$ROOT"
python3 bench.py run --shell "$GNU" --name gnu --out results --reps 5 \
  || { echo "GNU RUN FAILED"; echo FAIL > "$WORK/gap-v1.done"; exit 1; }
GJ=$(ls -t results/*-gnu.json | head -1)
echo "gnu results: $GJ (load now $(load1))"
python3 bench.py run --shell "$RUBASH" --name rubash --out results --reps 5 \
  || { echo "RUBASH RUN FAILED"; echo FAIL > "$WORK/gap-v1.done"; exit 1; }
RJ=$(ls -t results/*-rubash.json | head -1)
echo "rubash results: $RJ (load now $(load1))"
python3 bench.py gap "$RJ" "$GJ" --out results/gap-v1.md || true
echo "=== run_gap_v1 done $(date -Is) ==="
echo OK > "$WORK/gap-v1.done"
