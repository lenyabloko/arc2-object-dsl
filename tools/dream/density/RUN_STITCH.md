# Stitch over the generator-module corpus (Fable v14 O3 / T76) — WSL session, run once

Approved by Len (Oct 2, ~04:15 EDT): Rust toolchain via rustup in user space if missing, git clone of
mlb2251/stitch, cargo build (crates from crates.io). Nothing system-wide, nothing deleted, nothing Kaggle-related.
Start only after the Windows session reports c45-v35-parity done (its timing must not be disturbed).

1. `cargo --version` — if missing:
   `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal && . "$HOME/.cargo/env"`
2. `mkdir -p ~/arc/stitch && cd ~/arc/stitch && git clone https://github.com/mlb2251/stitch.git src && cd src &&
    git checkout 350804b7b35807c78bd21c313785ae5152ae2985 && cargo build --release --bin compress`
   (record the build time; if the build fails, report the first error line and stop.)
3. Run on the small corpus first (2,263 programs, functions of 8–300 AST nodes), from the repo root:
   `timeout 2700 ~/arc/stitch/src/target/release/compress results/o0/stitch_corpus_small.json -a 3 -i 25 -t 2 --out ~/arc/stitch/out_small.json`
   then, only if that finished in under 30 minutes, the full corpus (3,156 programs):
   `timeout 3600 ~/arc/stitch/src/target/release/compress results/o0/stitch_corpus.json -a 3 -i 25 -t 2 --out ~/arc/stitch/out_full.json`
4. Copy the output json(s) to `C:\Users\lenya\arc_extended_arga\cloud_outbox\wsl_results\stitch\` (out_small.json,
   out_full.json) and report: rustup used (y/n), build minutes, per run: exit status, minutes, number of abstractions,
   final compression ratio (the last "compression" line Stitch prints). Do not paste the abstractions themselves.
5. Do not touch submission/, tools/, ~/arc/.hid_salt or any wake job. The v20 submission after 20:00 EDT stays first
   priority; stop Stitch at 19:45 EDT if it is still running.
