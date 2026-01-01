# LLM-Assisted Data Cleaning (Local, Reproducible)

A small tool I built to speed up CSV data cleaning. It combines:
- Deterministic, auditable checks with pandas (missing values, duplicates)
- A compact full-dataset summary + random sample (up to 50 rows)
- Optional local LLM suggestions via Ollama (no data leaves the machine)
- A conservative “cleaned CSV” export (trim spaces, coerce obvious types, drop duplicates)

I keep the LLM in an advisory role. All actual cleaning actions are deterministic.

## Demo (What it looks like)
- Upload CSV → Analyze → See baseline + LLM suggestions → Optionally download cleaned CSV.

## Features
- Baseline checks: missing values, duplicates
- Full-dataset per-column summary (dtype, nulls, uniques, min/max, examples)
- Random sample for concrete examples (default n=50)
- Local LLM via `ollama run` (default model: `gemma:2b`)
- Deterministic cleaner: trims strings, attempts numeric/datetime coercion, drops duplicates

## Requirements
- macOS/Linux recommended (tested on macOS)
- Python 3.9+
- [Ollama](https://ollama.com) installed if you want LLM suggestions (optional)
- `gemma:2b` model pulled locally (optional):  
  ```bash
  ollama pull gemma:2b
  ```

## Install
Create and activate a virtual environment, then install deps:
```bash
python3 -m venv venv
./venv/bin/python -m pip install --upgrade pip
./venv/bin/pip install gradio==4.43.0 gradio-client==1.3.0 fastapi==0.110.0 pandas
```

Why pin versions?
- Avoids a known Gradio JSON-schema error with newer combos.

## Run
```bash
./venv/bin/python app.py
```
If localhost is blocked, the app uses `share=True` and will print a public link.
Open the printed URL to access the UI.

## Usage
1. Click “Upload CSV”, pick your file.
2. Click “Analyze”.
   - You’ll see:
     - Baseline (pandas) report
     - LLM suggestions (if Ollama is installed and a model is pulled)
3. Click “Generate cleaned CSV (download)” to save a conservative cleaned file.

<img src="Research_Project_latex_paper/Screenshot%202025-09-30%20at%2000.33.57.png" width="80%">

Notes:
- LLM suggestions do not change your data.
- The cleaned file is produced by a deterministic routine in `generate_cleaned_csv`.

## Configuration
- Model name: change in `query_ollama(model=\"gemma:2b\")` inside `app.py`.
- Timeout: `timeout_seconds` in `query_ollama`.
- Sample size: in `analyze_file`, change `sample_n = 50`.
- Prompt: edit the template in `analyze_file` to tune style and constraints.

## How It Works
- `app.py`:
  - `analyze_file`: reads CSV, runs pandas checks, builds per-column summary, samples up to 50 rows, constructs prompt, calls Ollama, renders results.
  - `_build_dataset_summary`: per-column dtype, nulls, uniques, min/max (for numeric), example values.
  - `generate_cleaned_csv`: trims whitespace, attempts numeric and datetime coercions, drops duplicates, writes a temp CSV for download.
- Frontend: Gradio `Blocks` UI.

## Data Privacy
- All analysis and LLM inference happen locally (if using Ollama).
- Only the dataset summary and sample rows are passed to the model process on your machine.

## Troubleshooting
- “No module named gradio”:
  - Install deps in venv: `./venv/bin/pip install gradio pandas`
- Python 3.9 type hints error (`str | None`):
  - Fixed by using `Optional[str]` in `app.py`
- Gradio JSON schema error (`TypeError: argument of type 'bool' is not iterable`):
  - Use pinned versions above (Gradio 4.43.0, gradio-client 1.3.0, FastAPI 0.110.0)
- Localhost blocked / no URL:
  - The app uses `share=True` and should show a public link. If not, check proxy/VPN.
- Ollama errors:
  - Ensure `ollama` is on PATH and model pulled: `ollama pull gemma:2b`
  - Increase timeout in `query_ollama(..., timeout_seconds=180)`

## Example Datasets
- `data/noisy_20k.csv`: synthetic noisy data generated for evaluation
- `data/sample_test.csv`: small sample for quick checks

## Roadmap / Ideas
- Add UI slider for sample size
- Add richer profiling (nulls, uniques, inferred type per column)
- Let the LLM propose a structured “plan” (YAML/JSON), validate, then apply deterministically

## Citation
If you use or build on this, please cite:
- Abedjan et al., 2016 (data errors)
- Polyzotis et al., 2019 (ML data mgmt)
- Wang & Strong, 1996 (data quality)
