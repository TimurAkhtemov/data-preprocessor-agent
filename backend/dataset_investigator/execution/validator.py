"""Deliberately small analytical language; AST filtering is not a security boundary alone."""

import ast

SAFE_BUILTINS = {
    "len",
    "min",
    "max",
    "sum",
    "sorted",
    "round",
    "abs",
    "enumerate",
    "range",
    "list",
    "dict",
    "set",
    "tuple",
    "float",
    "int",
    "str",
    "bool",
    "zip",
    "any",
    "all",
}
BLOCKED_NAMES = {
    "os",
    "sys",
    "subprocess",
    "socket",
    "pathlib",
    "shutil",
    "requests",
    "httpx",
    "urllib",
    "builtins",
    "importlib",
    "pickle",
    "marshal",
    "ctypes",
    "open",
    "exec",
    "eval",
    "compile",
    "globals",
    "locals",
    "vars",
    "input",
    "getattr",
    "setattr",
    "delattr",
    "type",
    "help",
    "breakpoint",
    "memoryview",
    "object",
    "super",
}
MODULE_MEMBERS = {
    "pd": {
        "DataFrame",
        "Series",
        "crosstab",
        "to_numeric",
        "to_datetime",
        "cut",
        "qcut",
        "concat",
        "isna",
        "notna",
        "isnull",
        "notnull",
        "unique",
        "NA",
        "NaT",
        "Timestamp",
        "Timedelta",
    },
    "np": {
        "array",
        "asarray",
        "arange",
        "linspace",
        "where",
        "select",
        "isfinite",
        "isnan",
        "isinf",
        "abs",
        "sqrt",
        "log",
        "log1p",
        "exp",
        "mean",
        "median",
        "std",
        "var",
        "sum",
        "min",
        "max",
        "nanmean",
        "nanmedian",
        "nanstd",
        "nansum",
        "quantile",
        "percentile",
        "nanquantile",
        "nanpercentile",
        "histogram",
        "unique",
        "sort",
        "argsort",
        "corrcoef",
        "cov",
        "clip",
        "round",
        "floor",
        "ceil",
        "concatenate",
        "column_stack",
        "vstack",
        "hstack",
        "nan",
        "inf",
    },
    "stats": {
        "skew",
        "kurtosis",
        "iqr",
        "zscore",
        "pearsonr",
        "spearmanr",
        "kendalltau",
        "chi2_contingency",
        "ttest_ind",
        "mannwhitneyu",
        "ks_2samp",
        "describe",
        "median_abs_deviation",
        "variation",
        "normaltest",
        "shapiro",
    },
}
SAFE_ATTRIBUTES = {
    "loc",
    "iloc",
    "at",
    "iat",
    "str",
    "dt",
    "cat",
    "index",
    "columns",
    "values",
    "shape",
    "size",
    "ndim",
    "dtype",
    "dtypes",
    "empty",
    "name",
    "T",
    "groupby",
    "agg",
    "aggregate",
    "transform",
    "describe",
    "value_counts",
    "nunique",
    "unique",
    "count",
    "size",
    "mean",
    "median",
    "std",
    "var",
    "min",
    "max",
    "sum",
    "quantile",
    "skew",
    "kurt",
    "corr",
    "cov",
    "cumsum",
    "cumcount",
    "rank",
    "diff",
    "pct_change",
    "round",
    "abs",
    "clip",
    "between",
    "isin",
    "isna",
    "notna",
    "isnull",
    "notnull",
    "any",
    "all",
    "duplicated",
    "drop_duplicates",
    "dropna",
    "fillna",
    "replace",
    "sort_values",
    "sort_index",
    "head",
    "tail",
    "nlargest",
    "nsmallest",
    "reset_index",
    "set_index",
    "rename",
    "rename_axis",
    "reindex",
    "astype",
    "copy",
    "assign",
    "melt",
    "pivot",
    "pivot_table",
    "unstack",
    "stack",
    "transpose",
    "to_frame",
    "to_list",
    "tolist",
    "to_dict",
    "to_numpy",
    "select_dtypes",
    "sample",
    "items",
    "keys",
    "get",
    "strip",
    "lstrip",
    "rstrip",
    "lower",
    "upper",
    "casefold",
    "contains",
    "startswith",
    "endswith",
    "len",
    "match",
    "fullmatch",
    "extract",
    "split",
    "slice",
    "year",
    "month",
    "day",
    "dayofweek",
    "hour",
    "date",
    "floor",
    "ceil",
    "total_seconds",
    "normalize",
    "strftime",
    "categories",
    "codes",
    "statistic",
    "pvalue",
    "correlation",
    "nobs",
    "minmax",
    "variance",
    "skewness",
    "kurtosis",
    "item",
    "reshape",
    "flatten",
    "ravel",
    "argmax",
    "argmin",
    "argsort",
    "all",
    "any",
    "append",
    "extend",
    "update",
}
AGGREGATIONS = {
    "count",
    "size",
    "mean",
    "median",
    "std",
    "var",
    "min",
    "max",
    "sum",
    "first",
    "last",
    "nunique",
    "skew",
    "any",
    "all",
    "prod",
    "sem",
}
BLOCKED_NODES = (
    ast.Import,
    ast.ImportFrom,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Lambda,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.Raise,
    ast.Global,
    ast.Nonlocal,
    ast.Delete,
    ast.Await,
    ast.Yield,
    ast.YieldFrom,
    ast.Starred,
)


class CodeRejected(ValueError):
    pass


def _aggregation(value):
    """Pandas accepts method names as strings; prevent indirect I/O/eval dispatch."""
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        if value.value not in AGGREGATIONS:
            raise CodeRejected("Aggregation must use an allowed statistical function name.")
    elif isinstance(value, (ast.List, ast.Tuple)):
        for item in value.elts:
            _aggregation(item)
    elif isinstance(value, ast.Dict):
        for item in value.values:
            _aggregation(item)
    else:
        raise CodeRejected("Use literal statistical names in agg/aggregate/transform.")


def validate_code(code: str) -> ast.Module:
    if len(code) > 8000:
        raise CodeRejected("Analytical code is limited to 8,000 characters.")
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise CodeRejected(f"Invalid Python syntax on line {exc.lineno}.") from exc
    if sum(1 for _ in ast.walk(tree)) > 1500:
        raise CodeRejected("Analysis is too complex; use a smaller expression.")
    assigned = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
    }
    problems = []
    nodes = list(ast.walk(tree))
    if any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in nodes):
        problems.append("Remove all imports: df, pd, np and stats are already available.")
    if any(isinstance(node, ast.Lambda) for node in nodes):
        problems.append(
            "Lambda is unavailable; create a boolean column with assign, then aggregate it with sum/mean."
        )
    if any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print"
        for node in nodes
    ):
        problems.append("Remove print(...). The worker captures the variable result automatically.")
    if "result" not in assigned:
        problems.append("Assign the final analytical value to result, exactly that variable name.")
    if problems:
        raise CodeRejected(" ".join(problems))
    attribute_bases = {
        id(node.value)
        for node in nodes
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
    }
    for node in nodes:
        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and node.id in MODULE_MEMBERS
            and id(node) not in attribute_bases
        ):
            raise CodeRejected(
                f"Use {node.id} directly with attribute access; modules cannot be aliased or passed as values."
            )
    for node in ast.walk(tree):
        if isinstance(node, BLOCKED_NODES):
            raise CodeRejected(f"{type(node).__name__} is not allowed in analytical Python.")
        if isinstance(node, ast.Name):
            if node.id.startswith("_") or node.id in BLOCKED_NAMES:
                raise CodeRejected(f"Name {node.id!r} is not available.")
            if isinstance(node.ctx, ast.Store) and node.id in (set(MODULE_MEMBERS) | SAFE_BUILTINS):
                raise CodeRejected("Do not overwrite analytical modules or builtins.")
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                raise CodeRejected("Private and dunder attributes are not allowed.")
            if isinstance(node.value, ast.Name) and node.value.id in MODULE_MEMBERS:
                if node.attr not in MODULE_MEMBERS[node.value.id]:
                    raise CodeRejected(
                        f"{node.value.id}.{node.attr} is not an allowed analytical operation."
                    )
            elif node.attr not in SAFE_ATTRIBUTES:
                raise CodeRejected(
                    f"Attribute {node.attr!r} is not an allowed analytical operation. Use df['column'] for column access."
                )
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id not in SAFE_BUILTINS:
                    raise CodeRejected(
                        f"Callable {node.func.id!r} is not available. Use explicit pandas/numpy/scipy analytical methods and assign output to result."
                    )
            elif not isinstance(node.func, ast.Attribute):
                raise CodeRejected("Indirect or dynamically constructed calls are not allowed.")
            if isinstance(node.func, ast.Attribute) and node.func.attr in {
                "agg",
                "aggregate",
                "transform",
            }:
                for arg in node.args:
                    _aggregation(arg)
                for keyword in node.keywords:
                    if keyword.arg in {"func"}:
                        _aggregation(keyword.value)
                    elif keyword.arg not in {"axis", "numeric_only"}:
                        # Named aggregation: output=(column, statistical_function).
                        if not isinstance(keyword.value, ast.Tuple) or len(keyword.value.elts) != 2:
                            raise CodeRejected("Named aggregation requires (column, function).")
                        _aggregation(keyword.value.elts[1])
            if isinstance(node.func, ast.Attribute) and node.func.attr == "pivot_table":
                for keyword in node.keywords:
                    if keyword.arg == "aggfunc":
                        _aggregation(keyword.value)
                if len(node.args) > 3:
                    raise CodeRejected("Use keyword arguments for pivot_table aggregation.")
            if any(k.arg is None for k in node.keywords):
                raise CodeRejected("Expanded keyword arguments are not allowed.")
    return tree
