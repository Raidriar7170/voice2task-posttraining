# Public Readiness Checklist

- [x] Public sample SFT JSONL exists under `data/public-samples/`.
- [x] Public sample DPO JSONL exists under `data/public-samples/`.
- [x] Public manifest records counts, splits, rejection categories, and source summary.
- [x] Local/private corpus output paths are gitignored.
- [x] SFT dry-run adapter metadata exists and says `release_status = not_released`.
- [x] DPO dry-run adapter metadata exists and says `release_status = not_released`.
- [x] Metrics JSON and Markdown report exist for the public sample.
- [x] Leak scan passes on committed public artifacts and reports, including public/private provenance markers in JSONL rows.
- [x] OpenSpec tasks reflect completed work only after validation commands pass.
- [x] No README/report wording claims a released checkpoint, full public corpus, or live-browser improvement.
- [x] Real SFT/DPO training entrypoints are present behind explicit `--run-training` and `allow_heavy_training` opt-in.
