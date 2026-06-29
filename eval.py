#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Minimal sequential Gemini eval. Prints only the final score.")
    parser.add_argument("--dataset", required=True, help="Dataset JSON path. Supports a JSON list or {'items': [...]}.")
    parser.add_argument("--model", default=os.getenv("GEMINI_MODEL", "gemini-3-pro-preview"))
    parser.add_argument("--api-key", default=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    parser.add_argument("--base-url", default=os.getenv("GOOGLE_GEMINI_BASE_URL", ""))
    parser.add_argument(
        "--output",
        default=None,
        help="Prediction JSONL path. Defaults to <dataset_stem>_predictions.jsonl next to the dataset.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Optional first-N debug limit.")
    parser.add_argument("--sleep", type=float, default=0.0, help="Optional delay between requests.")
    return parser.parse_args()


def load_items(dataset_path: Path) -> list[dict[str, Any]]:
    with dataset_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict) and isinstance(raw.get("items"), list):
        raw = raw["items"]
    if not isinstance(raw, list):
        raise ValueError(f"{dataset_path} must contain a JSON list or an object with an items list")
    return [dict(item) for item in raw if isinstance(item, dict)]


def resolve_path(value: object, dataset_dir: Path) -> Path | None:
    text = str(value or "").strip()
    if not text or text == ".":
        return None
    path = Path(text)
    if path.is_absolute():
        return path
    return (dataset_dir / path).resolve()


def iter_path_values(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v or "").strip() for v in value if str(v or "").strip()]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return [stripped]
            return iter_path_values(parsed)
        return [stripped]
    return [str(value).strip()] if str(value).strip() else []


def guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def make_client(api_key: str, base_url: str):
    try:
        from google import genai
        from google.genai import types
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing dependency: google-genai. Install with: uv pip install google-genai"
        ) from exc

    if base_url:
        os.environ["GOOGLE_GEMINI_BASE_URL"] = base_url
        try:
            return genai.Client(api_key=api_key, http_options=types.HttpOptions(base_url=base_url)), types
        except TypeError:
            return genai.Client(api_key=api_key), types
    return genai.Client(api_key=api_key), types


def build_contents(item: dict[str, Any], dataset_dir: Path, types: Any) -> list[Any]:
    question = str(item.get("question") or item.get("text") or "").strip()
    if not question:
        raise ValueError(f"Item {item.get('id', '<no id>')} has no question/text")

    contents: list[Any] = [question]

    video_path = resolve_path(item.get("video_path") or item.get("path"), dataset_dir)
    if video_path is not None:
        if not video_path.is_file():
            raise FileNotFoundError(f"Video not found for item {item.get('id', '<no id>')}: {video_path}")
        contents.append(types.Part.from_bytes(data=video_path.read_bytes(), mime_type=guess_mime(video_path)))

    for field in ("image_gt", "image_paths"):
        for raw_path in iter_path_values(item.get(field)):
            image_path = resolve_path(raw_path, dataset_dir)
            if image_path is not None and image_path.is_file():
                contents.append(types.Part.from_bytes(data=image_path.read_bytes(), mime_type=guess_mime(image_path)))

    return contents


def extract_answer(text: object) -> str:
    response = str(text or "").strip()
    match = re.search(r"<answer>\s*(.*?)\s*</answer>", response, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return response.strip()


def normalize_answer(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    text = text.strip("`").strip()
    if text.startswith("{") or text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return re.sub(r"\s+", "", text).casefold()
        return json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":")).casefold()

    explicit = re.match(r"^\s*([A-Z])\s*(?:[.)。,:：;；-].*)?$", text, flags=re.IGNORECASE)
    if explicit:
        return explicit.group(1).casefold()

    text = re.sub(r"^\s*(?:final\s+answer|answer|option|choice)\s*(?:is|:|：)\s*", "", text, flags=re.IGNORECASE)
    text = text.strip().strip("`*").rstrip("。.,;:!?！？")
    text = re.sub(r"\s+", " ", text)
    return text.casefold()


def is_correct(item: dict[str, Any], response_text: object) -> bool:
    pred = normalize_answer(extract_answer(response_text))
    gt = normalize_answer(item.get("answer"))
    return bool(gt) and bool(pred) and pred == gt


def default_output_path(dataset_path: Path) -> Path:
    return dataset_path.with_name(f"{dataset_path.stem}_predictions.jsonl")


def prediction_record(
    item: dict[str, Any],
    index: int,
    model: str,
    response_text: str,
    error: str | None,
) -> dict[str, Any]:
    extracted_prediction = extract_answer(response_text)
    normalized_prediction = normalize_answer(extracted_prediction)
    normalized_answer = normalize_answer(item.get("answer"))
    correct = bool(normalized_answer) and bool(normalized_prediction) and normalized_prediction == normalized_answer
    return {
        "index": index,
        "id": item.get("id"),
        "model": model,
        "parent_major": item.get("parent_major"),
        "major": item.get("major"),
        "category": item.get("category"),
        "difficulty": item.get("difficulty"),
        "video_path": item.get("video_path") or item.get("path"),
        "image_paths": item.get("image_paths"),
        "question": item.get("question") or item.get("text"),
        "answer": item.get("answer"),
        "response_text": response_text,
        "extracted_prediction": extracted_prediction,
        "normalized_prediction": normalized_prediction,
        "normalized_answer": normalized_answer,
        "correct": correct,
        "error": error,
    }


def main() -> int:
    args = parse_args()
    if not args.api_key:
        raise SystemExit("Missing API key. Set GEMINI_API_KEY or pass --api-key.")
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be >= 1")

    dataset_path = Path(args.dataset).resolve()
    dataset_dir = dataset_path.parent
    output_path = Path(args.output).resolve() if args.output else default_output_path(dataset_path)
    items = load_items(dataset_path)
    if args.limit is not None:
        items = items[: args.limit]
    if not items:
        raise SystemExit("No eval items found.")

    client, types = make_client(str(args.api_key), str(args.base_url or ""))

    correct = 0
    total = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as out_file:
        for index, item in enumerate(items):
            error = None
            try:
                response = client.models.generate_content(
                    model=str(args.model),
                    contents=build_contents(item, dataset_dir, types),
                )
                response_text = getattr(response, "text", "") or ""
            except Exception as exc:
                response_text = ""
                error = f"{type(exc).__name__}: {exc}"
                print(f"[warning] {item.get('id', '<no id>')}: {error}", file=sys.stderr)

            record = prediction_record(item, index, str(args.model), response_text, error)
            out_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_file.flush()

            total += 1
            if record["correct"]:
                correct += 1

            if args.sleep > 0 and total < len(items):
                time.sleep(args.sleep)

    score = correct / total if total else 0.0
    print(f"predictions: {output_path}", file=sys.stderr)
    print(f"{correct}/{total} = {score:.4%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
