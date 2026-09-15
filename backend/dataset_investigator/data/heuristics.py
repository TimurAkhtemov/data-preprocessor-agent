import hashlib

from ..models import DatasetProfile, ProfilerFinding


def detect_findings(profile: DatasetProfile) -> list[ProfilerFinding]:
    findings = []

    def add(category, severity, title, description, columns, evidence, sampled=False):
        if sampled:
            evidence = {
                **evidence,
                "basis": f"Deterministic sample of {profile.sample_size:,} rows",
            }
            description += " Counts and distribution statistics describe the sample."
        key = category + ":" + ":".join(columns)
        findings.append(
            ProfilerFinding(
                id=hashlib.sha256(key.encode()).hexdigest()[:16],
                category=category,
                severity=severity,
                title=title,
                description=description,
                columns=columns,
                evidence=evidence,
            )
        )

    if profile.duplicate_rows:
        r = profile.duplicate_ratio
        add(
            "duplicates",
            "low" if r < 0.01 else "medium" if r < 0.05 else "high",
            f"{profile.duplicate_rows:,} repeated rows",
            "Exact duplicates across all columns, excluding the first occurrence. Repeated records may be intentional; inspect their source before removing them.",
            [],
            {
                "duplicate_rows": profile.duplicate_rows,
                "duplicate_ratio": r,
                "basis": "Full dataset",
            },
        )
    for c in profile.columns:
        if c.missing_ratio >= 0.01:
            add(
                "missingness",
                "high" if c.missing_ratio > 0.3 else "medium" if c.missing_ratio >= 0.05 else "low",
                f"{c.missing_ratio:.1%} of {c.name} is missing",
                "Missing values may reflect collection or source-specific coverage. Check the affected records before choosing a treatment.",
                [c.name],
                {
                    "missing_count": c.missing_count,
                    "missing_ratio": c.missing_ratio,
                    "basis": "Full dataset",
                },
            )
        if c.unique_count <= 1:
            add(
                "constant",
                "low",
                f"{c.name} is constant" if c.unique_count else f"{c.name} has no observed values",
                "This column contains at most one distinct non-null value.",
                [c.name],
                {"unique_count": c.unique_count},
            )
        elif c.most_common_ratio >= 0.99:
            add(
                "near_constant",
                "low",
                f"{c.name} is nearly constant",
                f"One value accounts for {c.most_common_ratio:.1%} of non-null observations.",
                [c.name],
                {"most_common_ratio": c.most_common_ratio},
            )
        if c.inferred_type == "identifier-like":
            add(
                "identifier",
                "low",
                f"{c.name} appears identifier-like",
                "Column is nearly unique across rows and may function as an identifier.",
                [c.name],
                {"unique_count": c.unique_count, "unique_ratio": c.unique_ratio},
            )
        if c.stored_as_text and c.inferred_type in {"numeric", "datetime"}:
            add(
                "type_mismatch",
                "low",
                f"{c.name} stores {c.inferred_type} values as text",
                "More than 90% of sampled non-null values parse as this type. Original values are preserved.",
                [c.name],
                {"stored_dtype": c.pandas_dtype, "inferred_type": c.inferred_type},
                profile.sampled,
            )
        cat = c.categorical_stats
        if cat and cat.normalization_collisions:
            add(
                "categorical_consistency",
                "medium",
                f"Possible inconsistent labels in {c.name}",
                f"{cat.raw_unique_count:,} raw labels collapse to {cat.normalized_unique_count:,} after trimming, lowercasing and collapsing whitespace. Equivalence requires context.",
                [c.name],
                {
                    "raw_unique_count": cat.raw_unique_count,
                    "normalized_unique_count": cat.normalized_unique_count,
                    "examples": cat.normalization_collisions,
                },
                profile.sampled,
            )
        n = c.numeric_stats
        if not n:
            continue
        if n.non_finite_count:
            add(
                "non_finite",
                "medium",
                f"Non-finite values in {c.name}",
                "Infinite values are excluded from finite distribution statistics.",
                [c.name],
                {"non_finite_count": n.non_finite_count},
                profile.sampled,
            )
        if n.extreme_outlier_count:
            add(
                "outliers",
                "medium" if n.extreme_outlier_ratio > 0.01 else "low",
                f"{n.extreme_outlier_count:,} extreme statistical observations in {c.name}",
                "Observations fall outside Q1 − 3 × IQR or Q3 + 3 × IQR. Statistical extremes are not necessarily invalid.",
                [c.name],
                {
                    "extreme_outlier_count": n.extreme_outlier_count,
                    "extreme_outlier_ratio": n.extreme_outlier_ratio,
                    "lower_boundary": n.lower_extreme,
                    "upper_boundary": n.upper_extreme,
                },
                profile.sampled,
            )
        if n.skewness is not None and abs(n.skewness) > 2:
            add(
                "skew",
                "medium" if abs(n.skewness) > 5 else "low",
                f"{c.name} has a highly skewed distribution",
                "A long distribution tail can make the mean unrepresentative. Compare the median, quantiles and source groups.",
                [c.name],
                {"skewness": n.skewness, "mean": n.mean, "median": n.median},
                profile.sampled,
            )
        if (
            n.max is not None
            and n.p99 is not None
            and n.iqr is not None
            and (n.max - n.p99) > 10 * max(n.iqr, abs(n.p99) * 0.1, 1e-12)
        ):
            add(
                "extreme_gap",
                "medium",
                f"{c.name} maximum is far beyond its 99th percentile",
                "The maximum is separated from P99 by more than ten distribution-scale units. Inspect the tail for possible encoding or source effects.",
                [c.name],
                {"max": n.max, "p99": n.p99, "iqr": n.iqr},
                profile.sampled,
            )
    return sorted(findings, key=lambda f: ({"high": 0, "medium": 1, "low": 2}[f.severity], f.id))
