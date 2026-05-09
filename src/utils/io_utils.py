"""Safe file I/O utilities for reading and writing CSV files.

All file paths should come from config.py — never hardcode paths in
downstream scripts.
"""

from pathlib import Path
import pandas as pd


def read_csv(filepath: Path, **kwargs) -> pd.DataFrame:
    """Read a CSV file into a DataFrame.

    Args:
        filepath: Absolute or project-relative path to the CSV.
        **kwargs: Forwarded to pd.read_csv (e.g. encoding, dtype).

    Returns:
        DataFrame with the CSV contents.
    """
    return pd.read_csv(filepath, **kwargs)


def write_csv(df: pd.DataFrame, filepath: Path,
              index: bool = False, **kwargs) -> None:
    """Write a DataFrame to CSV, creating parent directories as needed.

    Args:
        df: DataFrame to persist.
        filepath: Destination path (parent dirs created if missing).
        index: Whether to write the DataFrame index column (default False).
        **kwargs: Forwarded to df.to_csv (e.g. encoding, sep).
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=index, **kwargs)
