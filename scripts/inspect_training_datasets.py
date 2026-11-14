
import pandas as pd
from pathlib import Path

files = [
    "bengaluru_complaints_telugu_reconstructed.csv",
    "translated_bengaluru_experimental_v1.csv",
    "translated_bengaluru_preprocessed_v1.csv",
    "translated_bengaluru_text_only_unflagged_v1.csv"
]

folder = Path("data/processed")

for filename in files:
    path = folder / filename

    print("\n" + "=" * 70)
    print("DATASET:", filename)

    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)

    print("Rows:", len(df))
    print("Columns:", list(df.columns))

    print("\nSample:")
    print(df.head(2).to_string(index=False))

    print("\nMissing values:")
    print(df.isnull().sum().to_string())

    for col in df.columns:
        if any(word in col.lower() for word in
               ["category", "label", "classification"]):
            print(f"\nDistribution: {col}")
            print(df[col].value_counts(dropna=False).head(30))
