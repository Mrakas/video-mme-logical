# Codex Reproduction Agent Guide

This document is a Codex-friendly reproduction guide for running the public
Video-MME-Logical evaluation from a clean machine. It describes what the agent
should do, what it should verify, and which commands should be executed.

The guide uses the current public release:

- GitHub repository: `https://github.com/Mrakas/video-mme-logical.git`
- Hugging Face dataset: `marcuskwan/video-mme-logical`
- Dataset archive: `video_mme_logical.zip`
- Default extracted dataset JSON: `data/video-mme-logical/three_level_testset.json`
- Evaluation script: repository-root `eval.py`

## What This Reproduces

The current public evaluator is a minimal sequential Gemini API evaluator. It
loads the benchmark JSON, attaches the corresponding video and optional image
inputs, sends each item to the configured Gemini model, writes JSONL prediction
records, and prints one final accuracy score.

This workflow can reproduce an API-model run on the released benchmark. To
reproduce the full paper leaderboard, repeat the same evaluation protocol for
each target model/API and compare the resulting scores with the paper tables.
The repository does not include private API keys or hosted model credentials.

## Paste-Ready Codex Prompt

Copy the prompt below into Codex on a machine with internet access, Python, git,
and enough disk space for the dataset archive and extracted videos. `uv` is
recommended; if it is unavailable, ask Codex to use the standard `venv` fallback
shown later in this document.

```text
You are reproducing Video-MME-Logical evaluation from the public release.

Goal:
1. Clone https://github.com/Mrakas/video-mme-logical.git.
2. Download the Hugging Face dataset marcuskwan/video-mme-logical.
3. Unzip video_mme_logical.zip.
4. Run the repository eval.py script with a Gemini API model.
5. Save JSONL predictions and report the final printed accuracy.

Important constraints:
- Do not commit API keys, downloaded data, predictions, or local artifacts.
- Use the dataset JSON at data/video-mme-logical/three_level_testset.json after unzip.
- If the extracted folder differs, locate three_level_testset.json and use that path.
- First run a small --limit 5 smoke test before running the full benchmark.
- If rate limits occur, rerun with --sleep set to a positive number.
- If uv is unavailable, create the environment with python3 -m venv and pip instead.

Commands:

git clone https://github.com/Mrakas/video-mme-logical.git
cd video-mme-logical

python3 -m pip install -U huggingface_hub
mkdir -p data
huggingface-cli download marcuskwan/video-mme-logical video_mme_logical.zip --repo-type dataset --local-dir data/hf
unzip data/hf/video_mme_logical.zip -d data

test -f data/video-mme-logical/three_level_testset.json
test -d data/video-mme-logical/videos

uv venv .venv
source .venv/bin/activate
uv pip install google-genai huggingface_hub

export GEMINI_API_KEY=your_key_here

python eval.py \
  --dataset data/video-mme-logical/three_level_testset.json \
  --model gemini-3-pro-preview \
  --limit 5 \
  --output runs/gemini-3-pro-preview_smoke_predictions.jsonl

python eval.py \
  --dataset data/video-mme-logical/three_level_testset.json \
  --model gemini-3-pro-preview \
  --output runs/gemini-3-pro-preview_predictions.jsonl

After the run, report:
- the command that was run,
- the prediction JSONL path,
- the final printed accuracy,
- any failed examples or API errors found in the JSONL records.
```

## Manual Step-by-Step Workflow

### 1. Clone the Repository

```bash
git clone https://github.com/Mrakas/video-mme-logical.git
cd video-mme-logical
```

The repository root should contain `README.md`, `eval.py`, and this
`doc_agent.md` file.

### 2. Download and Extract the Dataset

Install the Hugging Face command-line tool if it is not already available:

```bash
python3 -m pip install -U huggingface_hub
```

Download the released archive:

```bash
mkdir -p data
huggingface-cli download marcuskwan/video-mme-logical video_mme_logical.zip --repo-type dataset --local-dir data/hf
unzip data/hf/video_mme_logical.zip -d data
```

Verify the expected structure:

```bash
test -f data/video-mme-logical/three_level_testset.json
test -d data/video-mme-logical/videos
test -d data/video-mme-logical/images
```

If a check fails, search for the extracted JSON:

```bash
find data -name three_level_testset.json -print
```

Use the discovered JSON path in the `--dataset` argument. Relative video and
image paths are resolved from the directory containing that JSON file.

### 3. Create the Python Environment

The project uses a small evaluator dependency set. `uv` is recommended:

```bash
uv venv .venv
source .venv/bin/activate
uv pip install google-genai huggingface_hub
```

If `uv` is not installed, use a standard virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip google-genai huggingface_hub
```

### 4. Configure the API

Set one of the supported API key environment variables:

```bash
export GEMINI_API_KEY=your_key_here
```

`eval.py` also accepts:

- `GOOGLE_API_KEY` as an alternative key environment variable.
- `GEMINI_MODEL` as the default model name.
- `GOOGLE_GEMINI_BASE_URL` for an optional compatible endpoint or proxy.
- `--api-key` and `--base-url` command-line arguments.

Do not write real API keys into the repository or prediction files.

### 5. Run a Smoke Test

Run a small first-N check before the full benchmark:

```bash
python eval.py \
  --dataset data/video-mme-logical/three_level_testset.json \
  --model gemini-3-pro-preview \
  --limit 5 \
  --output runs/gemini-3-pro-preview_smoke_predictions.jsonl
```

The command should print a score like `x/5 = yy.yyyy%` and write the JSONL file
shown in the `predictions:` stderr line. Inspect any warnings before continuing.

### 6. Run the Full Evaluation

```bash
python eval.py \
  --dataset data/video-mme-logical/three_level_testset.json \
  --model gemini-3-pro-preview \
  --output runs/gemini-3-pro-preview_predictions.jsonl
```

For rate-limited APIs, add a delay between requests:

```bash
python eval.py \
  --dataset data/video-mme-logical/three_level_testset.json \
  --model gemini-3-pro-preview \
  --sleep 1.0 \
  --output runs/gemini-3-pro-preview_predictions.jsonl
```

The full run sends benchmark videos to the configured API. It can take time and
may incur API cost.

## Evaluator Arguments

- `--dataset`: Required path to the benchmark JSON. Supports a JSON list or an
  object with an `items` list.
- `--model`: Gemini model name. Defaults to `GEMINI_MODEL` or
  `gemini-3-pro-preview`.
- `--api-key`: Optional explicit API key. Defaults to `GEMINI_API_KEY` or
  `GOOGLE_API_KEY`.
- `--base-url`: Optional compatible Gemini endpoint. Defaults to
  `GOOGLE_GEMINI_BASE_URL`.
- `--output`: Prediction JSONL path. If omitted, the file is written next to the
  dataset JSON as `<dataset_stem>_predictions.jsonl`.
- `--limit`: Optional first-N debug limit.
- `--sleep`: Optional delay between requests.

Each JSONL record includes item metadata, raw model response text, extracted
answer, normalized prediction, normalized ground truth, correctness, and any
API error message.

## Troubleshooting

- `Missing API key`: set `GEMINI_API_KEY`, `GOOGLE_API_KEY`, or pass
  `--api-key`.
- `Missing dependency: google-genai`: activate the environment and run
  `uv pip install google-genai`.
- `Video not found`: verify that `three_level_testset.json`, `videos/`, and
  `images/` were extracted under the same dataset directory.
- `huggingface-cli: command not found`: run
  `python3 -m pip install -U huggingface_hub`.
- API rate limits or transient failures: use `--limit` for debugging, then retry
  the full run with `--sleep 1.0` or a larger delay.

## Extending Beyond Gemini

The current public script is intentionally minimal and targets Gemini through
`google-genai`. To evaluate another API provider, preserve the same dataset
loading, media path resolution, prediction JSONL schema, and answer-normalized
scoring behavior, then replace only the model request call.
