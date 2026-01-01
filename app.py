import gradio as gr
import pandas as pd
import subprocess
import tempfile
import os
import time
from typing import Optional


def query_ollama(prompt, model="gemma:2b", timeout_seconds: int = 120):
    # running ollama as a subprocess; model must be pulled already as in requirement
    try:
        p = subprocess.run(
            ["ollama", "run", model],
            input=prompt.encode("utf-8"),
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        return "ERROR: 'ollama' CLI not found. Install from https://ollama.com and ensure it is on PATH."
    except subprocess.TimeoutExpired:
        return f"ERROR: LLM call timed out after {timeout_seconds}s. Consider pulling the model first with 'ollama pull {model}'."

    stdout = (p.stdout or b"").decode("utf-8", errors="replace").strip()
    stderr = (p.stderr or b"").decode("utf-8", errors="replace").strip()

    if p.returncode != 0:
        # Surface stderr to help diagnose (e.g., model missing => it tries to download and can stall)
        return f"ERROR: ollama run failed (code {p.returncode}). Details: {stderr or 'No error details'}"

    # Some models may print extra newlines
    return stdout or (stderr if stderr else "No response from model.")


def _build_dataset_summary(df: pd.DataFrame) -> str:
    """Creating a compact, deterministic summary of the entire dataset for LLM context.

    For each column, report: dtype, non-null count, null count, unique count (capped
    display) and example values. Include simple numeric stats where applicable.
    """
    lines: list[str] = []
    num_rows, num_cols = df.shape
    lines.append(f"Rows: {num_rows}, Columns: {num_cols}")
    for column_name in df.columns:
        series = df[column_name]
        dtype_name = str(series.dtype)
        non_null = int(series.notna().sum())
        nulls = int(series.isna().sum())
        try:
            unique_count = int(series.nunique(dropna=True))
        except Exception:
            unique_count = -1

        # Collecting up to 3 example non-null values deterministically from head(), can be changed to n head count.
        example_values = series.dropna().astype(str).head(3).tolist()
        example_preview = ", ".join(example_values) if example_values else "(none)"

        # Numeric stats if convertible
        numeric_stats = ""
        if pd.api.types.is_numeric_dtype(series):
            try:
                min_val = series.min()
                max_val = series.max()
                numeric_stats = f", min={min_val}, max={max_val}"
            except Exception:
                numeric_stats = ""

        lines.append(
            f"- {column_name} | dtype={dtype_name}, non_null={non_null}, nulls={nulls}, unique={unique_count}{numeric_stats}; examples: {example_preview}"
        )

    return "\n".join(lines)


def analyze_file(file):
    start = time.perf_counter()
    yield "Reading CSV…", None, None
    try:
        df = pd.read_csv(file.name)
        source_name = os.path.basename(file.name)
    except Exception as e:
        yield f"Error reading file: {e}. Please upload a CSV.", None, None
        return

    # Baseline checks with pandas
    yield "Running baseline checks…", None, None
    issues = []
    if df.isnull().sum().sum() > 0:
        issues.append("Missing values found")
    if df.duplicated().sum() > 0:
        issues.append("Duplicate rows found")
    baseline_report = f"Pandas baseline detected: {', '.join(issues) if issues else 'No major issues'}"

    # LLM prompt: whole-dataset summary + random sample for better coverage
    dataset_summary = _build_dataset_summary(df)
    sample_n = 50 if len(df) >= 50 else len(df)
    sample_df = df.sample(n=sample_n, random_state=0) if sample_n > 0 else df.head(0)

    prompt = f"""
    You are a helpful data cleaning assistant for tabular CSV data.

    Dataset summary (entire file):
    {dataset_summary}

    Random sample of rows (up to 50):
    {sample_df.to_string(index=False)}

    Write your answer in exactly these three markdown sections with short bullet points:
    **1) Possible data quality issues:**
    - For each bullet, name the exact column and quote 1–2 example cell values from the sample.
    - Use the format: ColumnName: Issue → Action (keep one line per item).
    **2) Cleaning steps:**
    - Be concrete: specify target formats (e.g., YYYY-MM-DD), units (e.g., USD), and exact type casts (e.g., to int/float/category/datetime). No code.
    **3) Additional notes:**
    - Keep it practical; avoid vague words like "verify", "unexpected formats", or "might". If uncertain, say what to check and how.

    Rules:
    - Do not invent columns or values.
    - Do not include any code blocks.
    - Keep it concise and practical.
    """

    yield "Querying LLM…", None, None
    llm_response = query_ollama(prompt, model="gemma:2b")

    elapsed = time.perf_counter() - start
    summary = f"--- Baseline ---\n\n{baseline_report}\n\n--- LLM Suggestions ---\n\n{llm_response}\n\n_Time taken: {elapsed:.1f}s_"

    # Final yield includes the dataframe and name for later cleaning process.
    yield summary, df, source_name


def generate_cleaned_csv(df: pd.DataFrame, source_name: Optional[str]):
    if df is None:
        return None

    # Lightweight, deterministic cleaning (no LLM): keeps research separation clear
    cleaned = df.copy()

    # Striping whitespace in string columns
    for col in cleaned.select_dtypes(include=["object"]).columns:
        cleaned[col] = cleaned[col].astype(str).str.strip()

    # Trying to coerce obvious numeric columns (without deprecated arguments)
    for col in cleaned.columns:
        try:
            cleaned[col] = pd.to_numeric(cleaned[col])
        except Exception:
            # Leaves as-is if not purely numeric
            pass

    # Trying to parse any date-like columns without deprecated args
    for col in cleaned.columns:
        if cleaned[col].dtype == object:
            try:
                cleaned[col] = pd.to_datetime(cleaned[col])
            except Exception:
                pass

    # Droping exact duplicate rows
    cleaned = cleaned.drop_duplicates()

    # Writing to a temp file for download
    base = os.path.splitext(source_name or "cleaned.csv")[0]
    fd, tmp_path = tempfile.mkstemp(prefix=f"{base}_", suffix="_cleaned.csv")
    os.close(fd)
    cleaned.to_csv(tmp_path, index=False)
    return tmp_path


with gr.Blocks(css="#output-box { max-width: 100%; }") as demo:
    gr.Markdown("# LLM-assisted Data Cleaning Prototype")

    df_state = gr.State(None)
    name_state = gr.State("")

    with gr.Row():
        with gr.Column(scale=1):
            file_in = gr.File(label="Upload CSV")
            analyze_btn = gr.Button("Analyze", variant="primary")
        with gr.Column(scale=1):
            output_md = gr.Markdown(elem_id="output-box")

    with gr.Row():
        generate_btn = gr.Button("Generate cleaned CSV (download)")
        cleaned_file = gr.File(label="Cleaned CSV", interactive=False)

    analyze_btn.click(
        fn=analyze_file,
        inputs=[file_in],
        outputs=[output_md, df_state, name_state],
        show_progress=True,
    )

    generate_btn.click(
        fn=generate_cleaned_csv,
        inputs=[df_state, name_state],
        outputs=[cleaned_file],
        show_progress=True,
    )

if __name__ == "__main__":
    demo.launch(share=True)