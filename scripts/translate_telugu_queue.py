import argparse
import csv
import os
import tempfile
from pathlib import Path

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from IndicTransToolkit.processor import IndicProcessor

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "interim" / "telugu_translation_queue.csv"
MODEL_NAME = "ai4bharat/indictrans2-en-indic-dist-200M"

FIELDS = [
    "text_id", "source_field", "source_text", "target_language",
    "telugu_translation", "translation_provider", "translation_model",
    "translation_status", "review_status",
]

def save_queue(rows):
    fd, temp_name = tempfile.mkstemp(
        prefix="translation_queue_", suffix=".csv", dir=QUEUE.parent
    )
    os.close(fd)
    try:
        with open(temp_name, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temp_name, QUEUE)
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50,
                        help="Number of pending strings; 0 means all.")
    parser.add_argument("--batch-size", type=int, default=1)
    args = parser.parse_args()

    # Added validation checks
    if args.limit < 0:
        parser.error("--limit must be 0 or greater.")

    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1.")

    if not QUEUE.exists():
        raise FileNotFoundError(f"Translation queue not found: {QUEUE}")

    with QUEUE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise ValueError("Translation queue is empty.")

    for row in rows:
        for field in FIELDS:
            row.setdefault(field, "")

    pending = [
        i for i, row in enumerate(rows)
        if not (row.get("telugu_translation") or "").strip()
    ]
    if args.limit > 0:
        pending = pending[:args.limit]

    if not pending:
        print("No untranslated strings remain.")
        return

    # This laptop has CPU-only PyTorch; keep CPU thread usage bounded.
    torch.set_num_threads(min(4, torch.get_num_threads()))
    device = torch.device("cpu")

    print(f"Device: {device}")
    print(f"CPU threads: {torch.get_num_threads()}")
    print(f"Model: {MODEL_NAME}")
    print(f"Pending strings selected: {len(pending)}")
    print("Loading model. The first run may download model files...")

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME, trust_remote_code=True
    )
    model = AutoModelForSeq2SeqLM.from_pretrained(
        MODEL_NAME, trust_remote_code=True
    ).to(device)
    model.eval()

    processor = IndicProcessor(inference=True)
    completed = 0

    for start in range(0, len(pending), max(1, args.batch_size)):
        indices = pending[start:start + max(1, args.batch_size)]
        texts = [rows[i]["source_text"] for i in indices]

        try:
            prepared = processor.preprocess_batch(
                texts, src_lang="eng_Latn", tgt_lang="tel_Telu"
            )
            inputs = tokenizer(
                prepared,
                truncation=True,
                padding="longest",
                max_length=256,
                return_tensors="pt",
            ).to(device)

            with torch.inference_mode():
                generated = model.generate(
                    **inputs, num_beams=2, max_new_tokens=256
                )

            decoded = tokenizer.batch_decode(
                generated, skip_special_tokens=True
            )
            translated = processor.postprocess_batch(
                decoded, lang="tel_Telu"
            )

            for index, text in zip(indices, translated):
                rows[index]["telugu_translation"] = text.strip()
                rows[index]["translation_provider"] = "AI4Bharat"
                rows[index]["translation_model"] = MODEL_NAME
                rows[index]["translation_status"] = "TRANSLATED"
                rows[index]["review_status"] = "PENDING_HUMAN_REVIEW"

        except Exception as exc:
            for index in indices:
                rows[index]["translation_status"] = "ERROR_RETRY_REQUIRED"
            save_queue(rows)
            print(f"Translation failed at queue position {start + 1}: {exc}")
            print("Queue saved; correct the error before retrying.")
            raise

        completed += len(indices)
        save_queue(rows)
        print(f"Progress: {completed}/{len(pending)} selected strings")

    print(f"Completed this run: {completed}")
    print(f"Updated queue: {QUEUE}")
    print("Machine translations still require human review.")

if __name__ == "__main__":
    main()
