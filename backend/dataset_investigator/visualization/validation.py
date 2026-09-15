import numpy as np
import pandas as pd

from ..models import DatasetProfile
from .schemas import ChartSpec


def validate_chart(spec: ChartSpec, profile: DatasetProfile) -> ChartSpec:
    columns = {c.name: c for c in profile.columns}
    for name in (spec.x, spec.y, spec.color):
        if name is not None and name not in columns:
            raise ValueError(f"Unknown chart column: {name}")
    if spec.type == "missingness":
        if spec.x or spec.y or spec.color:
            raise ValueError("Missingness uses all columns; omit x, y and color.")
        return spec
    if not spec.x:
        raise ValueError("This chart requires an x column.")

    def numeric(name):
        return name is not None and columns[name].numeric_stats is not None

    if spec.type in {"histogram", "box", "scatter"} and not numeric(spec.x):
        raise ValueError(f"{spec.type} requires a numeric x column.")
    if spec.type == "scatter" and not numeric(spec.y):
        raise ValueError("Scatter requires a numeric y column.")
    if spec.type == "line" and columns[spec.x].inferred_type not in {"datetime", "numeric"}:
        raise ValueError("Line requires a datetime or numeric x column.")
    if spec.type in {"bar", "line"} and spec.y and not numeric(spec.y):
        raise ValueError("The y column must be numeric; omit y to count rows.")
    if spec.type in {"histogram", "box"} and spec.y:
        raise ValueError("Histogram and box charts use x, with optional color; omit y.")
    if spec.color and columns[spec.color].inferred_type not in {"categorical", "boolean"}:
        raise ValueError("Color must reference a categorical or boolean column.")
    return spec


def build_chart(spec: ChartSpec, df: pd.DataFrame, profile: DatasetProfile) -> dict:
    spec = validate_chart(spec, profile)
    sampled = profile.sampled
    data = df.sample(profile.sample_size, random_state=42) if sampled else df
    notes = []
    if sampled:
        notes.append(f"Distribution estimated from {len(data):,} sampled rows.")
    series = []
    if spec.type == "missingness":
        columns = sorted(
            [c for c in profile.columns if c.missing_count], key=lambda c: -c.missing_ratio
        )
        if len(columns) > 30:
            notes.append("Showing 30 columns with the highest missingness.")
        series = [
            {
                "name": "Missing values",
                "x": [c.missing_ratio * 100 for c in columns[:30]],
                "y": [c.name for c in columns[:30]],
            }
        ]
        sampled = False
        notes = [n for n in notes if not n.startswith("Distribution")]
    else:
        data = data[list(dict.fromkeys(n for n in [spec.x, spec.y, spec.color] if n))].copy()
        columns = {c.name: c for c in profile.columns}
        for name in [spec.x, spec.y]:
            if name and columns[name].numeric_stats:
                data[name] = pd.to_numeric(data[name], errors="coerce").replace(
                    [np.inf, -np.inf], np.nan
                )
        if spec.type in {"scatter", "box"} and len(data) > 5000:
            data = data.sample(5000, random_state=42)
            notes.append("Plot limited to a deterministic 5,000-row sample.")
            sampled = True
        groups = [("All rows", data)]
        if spec.color:
            # Group keys remain separate from original values, even for nulls.
            labels = data[spec.color].astype("string")
            missing_label = "(missing)"
            while missing_label in set(labels.dropna()):
                missing_label += " [null]"
            labels = labels.fillna(missing_label)
            top = labels.value_counts().head(8).index
            groups = [(str(name), data[labels == name]) for name in top]
            if labels.nunique() > 8:
                notes.append("Showing the eight most frequent color groups.")
        bin_edges = None
        if spec.type == "histogram":
            finite = data[spec.x].dropna().to_numpy(dtype=float)
            if len(finite):
                bin_edges = np.histogram_bin_edges(
                    finite, bins=min(40, max(5, int(np.sqrt(len(finite)))))
                )
        for name, group in groups:
            entry = {"name": name, "x": [], "y": []}
            if spec.type == "histogram" and bin_edges is not None:
                counts, edges = np.histogram(
                    group[spec.x].dropna().to_numpy(dtype=float), bins=bin_edges
                )
                entry.update(
                    x=((edges[:-1] + edges[1:]) / 2).tolist(),
                    y=counts.tolist(),
                    width=float(edges[1] - edges[0]) * 0.92,
                )
            elif spec.type == "box":
                entry["x"] = group[spec.x].dropna().tolist()
            elif spec.type == "scatter":
                clean = group.dropna(subset=[spec.x, spec.y])
                entry.update(x=clean[spec.x].tolist(), y=clean[spec.y].tolist())
            elif spec.type in {"bar", "line"}:
                x = group[spec.x]
                if spec.type == "line" and columns[spec.x].inferred_type == "datetime":
                    from ..data.profiler import to_dates

                    x = to_dates(x).dt.floor("D")
                if spec.y:
                    agg = group[spec.y].groupby(x, observed=True).mean().dropna()
                else:
                    agg = x.value_counts(dropna=True)
                if spec.type == "bar":
                    agg = agg.sort_values(ascending=False).head(spec.top_n or 20)
                else:
                    agg = agg.sort_index()
                    if len(agg) > 500:
                        # Coalesce adjacent ordered points instead of drawing thousands of points.
                        labels = np.arange(len(agg)) * 500 // len(agg)
                        if spec.y:
                            counts = (
                                group[spec.y].groupby(x, observed=True).count().reindex(agg.index)
                            )
                            temp = pd.DataFrame(
                                {
                                    "x": agg.index,
                                    "value": agg.values * counts.values,
                                    "count": counts.values,
                                    "bin": labels,
                                }
                            )
                            temp = temp.groupby("bin").agg(
                                {"x": "first", "value": "sum", "count": "sum"}
                            )
                            temp["value"] = temp["value"] / temp["count"]
                        else:
                            temp = pd.DataFrame(
                                {"x": agg.index, "value": agg.values, "bin": labels}
                            )
                            temp = temp.groupby("bin").agg({"x": "first", "value": "sum"})
                        agg = pd.Series(temp.value.to_numpy(), index=temp.x)
                        notes.append("Time/ordered values grouped into at most 500 adjacent bins.")
                entry.update(x=[str(v)[:200] for v in agg.index], y=agg.astype(float).tolist())
            series.append(entry)
    return {
        "spec": spec.model_dump(),
        "series": series,
        "sampled": sampled,
        "sample_size": len(data),
        "note": " ".join(dict.fromkeys(notes)),
        "aggregation": "mean" if spec.y and spec.type in {"bar", "line"} else "count",
    }
