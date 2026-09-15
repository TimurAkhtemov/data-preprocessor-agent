import csv
import logging
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

log = logging.getLogger(__name__)


class DatasetError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def load_dataset(path: Path, extension: str) -> pd.DataFrame:
    if extension not in {".csv", ".parquet"}:
        raise DatasetError("UNSUPPORTED_FILE", "Choose a CSV or Parquet file.")
    if path.stat().st_size == 0:
        raise DatasetError(
            "EMPTY_FILE", "The file is empty. Choose a dataset with rows and columns."
        )
    try:
        if extension == ".csv":
            frame = None
            for encoding in ("utf-8", "utf-8-sig", "latin-1"):
                try:
                    # Pandas accepts ragged rows and renames duplicate headers; fail explicitly.
                    with path.open(encoding=encoding, newline="") as stream:
                        reader = csv.reader(stream, strict=True)
                        header = next(reader)
                        if any("\x00" in field for field in header):
                            raise DatasetError(
                                "MALFORMED_CSV",
                                "CSV contains NUL characters; export it again as text.",
                            )
                        header = [h.lstrip("\ufeff") for h in header]
                        if not header or any(not h.strip() for h in header):
                            raise DatasetError("INVALID_COLUMNS", "CSV headers must be non-empty.")
                        if len(set(header)) != len(header):
                            raise DatasetError(
                                "INVALID_COLUMNS", "CSV contains duplicate column names."
                            )
                        for number, row in enumerate(reader, start=2):
                            if any("\x00" in field for field in row):
                                raise DatasetError(
                                    "MALFORMED_CSV",
                                    f"CSV row {number} contains NUL characters; export it again as text.",
                                )
                            if row and len(row) != len(header):
                                raise DatasetError(
                                    "MALFORMED_CSV",
                                    f"CSV row {number} has {len(row)} fields; expected {len(header)}. Check delimiters and quoting.",
                                )
                    frame = pd.read_csv(
                        path, encoding=encoding, on_bad_lines="error", low_memory=False
                    )
                    break
                except UnicodeDecodeError:
                    continue
            if frame is None:
                raise DatasetError("PARSE_FAILED", "Could not decode this CSV.")
        else:
            schema = pq.read_schema(path)
            if any(
                pa.types.is_nested(field.type) or pa.types.is_binary(field.type) for field in schema
            ):
                raise DatasetError(
                    "UNSUPPORTED_COLUMNS",
                    "Use a flat tabular Parquet file; nested and binary columns are not supported.",
                )
            frame = pd.read_parquet(path)
        if len(frame.columns) == 0:
            raise DatasetError("EMPTY_DATASET", "The dataset has no columns.")
        if frame.empty:
            raise DatasetError("EMPTY_DATASET", "The dataset has headers but no rows.")
        frame.columns = frame.columns.map(str)
        if not frame.columns.is_unique or any(not c.strip() for c in frame.columns):
            raise DatasetError("INVALID_COLUMNS", "Column names must be unique and non-empty.")
        log.info("Dataset parsed: rows=%d columns=%d", len(frame), len(frame.columns))
        return frame.reset_index(drop=True)
    except DatasetError:
        raise
    except (ValueError, csv.Error, StopIteration, pa.ArrowException, OSError) as exc:
        log.info("Dataset parse failed: %s", type(exc).__name__)
        raise DatasetError(
            "PARSE_FAILED",
            "Could not parse this file. Check that it is a valid CSV or Parquet dataset with a header and consistent rows.",
        ) from exc
