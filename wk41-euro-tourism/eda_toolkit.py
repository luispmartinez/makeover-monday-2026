"""
eda_toolkit.py
--------------
A small, dependency-light EDA engine you can import into any project's
pipeline script, OR run automatically over a folder via scan_and_profile.py.

The core idea: DatasetProfiler takes a DataFrame, runs a fixed set of
profiling steps against it, and writes the results out as a Markdown report.
Nothing here is specific to Tableau, Met Office, or any one project — that's
what makes it reusable. Project-specific logic (like "average by season")
belongs in its own script that imports this module, not in here.
"""

from __future__ import annotations
# ^ lets us write type hints like `dict[str, str]` even on older Python
#   versions that would otherwise require `Dict[str, str]` from `typing`.

from pathlib import Path
from datetime import datetime

import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf
import itertools as it
import numpy as np



class DatasetProfiler:
    """Profiles one tabular dataset and builds a Markdown EDA report.

    Parameters
    ----------
    df : pd.DataFrame
        The data to profile. Loading the CSV is the caller's job — this
        class only ever deals with a DataFrame already in memory. That's a
        deliberate boundary: it means DatasetProfiler works identically
        whether the data came from a CSV, an API pull, or a SQL query.
    name : str
        A label used in the report header and default filenames.

    Usage
    -----
        profiler = DatasetProfiler(df, name="met_office")
        profiler.run()                      # do the analysis
        profiler.write_report("out.md")     # save it

    Or chained, since `run()` returns `self`:
        DatasetProfiler(df, name="met_office").run().write_report("out.md")
    """

    def __init__(self, df: pd.DataFrame, name: str = "dataset", exclude_columns: list[str] | None = None, min_category_size = 32, 
                 group = None,metric = None, percent = None, n = None, is_overall = None, is_overall_value = "Yes"):
        self.df = df
        self.name = name
        self.exclude_columns = exclude_columns if exclude_columns is not None else []
        self.min_category_size = min_category_size
        self.group = group
        self.metric = metric
        self.percent = percent
        self.n = n
        self.is_overall = is_overall
        self.is_overall_value = is_overall_value
        # sections is an ordered dict: {"shape": "## Shape\n\n...", ...}
        # Each profiling step below writes ONE entry. write_report() just
        # concatenates them in insertion order. Keeping each step's output
        # isolated like this means you can re-run just one step, inspect
        # `profiler.sections["missing"]` directly in a notebook, or reorder
        # sections later without touching the profiling logic itself.
        self.sections: dict[str, str] = {}

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def run(self) -> "DatasetProfiler":
        """Run every profiling step. Returns self so calls can be chained."""
        self._profile_shape()
        self._profile_dtypes()
        self._profile_missing()
        self._profile_duplicates()
        self._profile_numeric()
        self._profile_categorical()
        self._profile_bivariate()
        self._profile_categorical_bivariate()
        self._profile_grouped()
        self._profile_ols()
        self._profile_categorical_categorical()
        return self

    def write_report(self, path: str | Path) -> Path:
        """Write the accumulated sections to a Markdown file and return the path."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        header = (
            f"# EDA Report — {self.name}\n\n"
            f"Generated {datetime.now():%Y-%m-%d %H:%M}\n"
        )
        body = "\n".join(self.sections.values())
        path.write_text(header + "\n" + body, encoding="utf-8")
        return path

    # ------------------------------------------------------------------ #
    # Profiling steps — each one is small and does exactly one job.
    # Leading underscore (_profile_shape) is a Python convention meaning
    # "internal, not part of the public API" — nothing enforces it, it's
    # just a signal to callers: "don't call this directly, it's a step
    # inside run()".
    # ------------------------------------------------------------------ #

    def _profile_shape(self) -> None:
        rows, cols = self.df.shape
        self.sections["shape"] = f"## Shape\n\n{rows:,} rows x {cols} columns\n"

    def _profile_dtypes(self) -> None:
        lines = "\n".join(f"- `{c}`: {t}" for c, t in self.df.dtypes.items())
        self.sections["dtypes"] = f"## Column types\n\n{lines}\n"

    def _profile_missing(self) -> None:
        missing = self.df.isna().sum()
        missing = missing[missing > 0]  # boolean mask: keep only columns with >0 missing
        if missing.empty:
            body = "No missing values in any column.\n"
        else:
            body = "\n".join(
                f"- `{c}`: {n:,} missing ({n / len(self.df):.1%})"
                for c, n in missing.items()
            )
        self.sections["missing"] = f"## Missing values\n\n{body}\n"

    def _profile_duplicates(self) -> None:
        n_dupes = int(self.df.duplicated().sum())
        self.sections["duplicates"] = (
            f"## Duplicate rows\n\n{n_dupes:,} fully duplicated rows\n"
        )

    def _profile_numeric(self) -> None:
        numeric_df = self.df.select_dtypes(include="number")
        if numeric_df.empty:
            self.sections["numeric"] = "## Numeric summary\n\nNo numeric columns.\n"
            return
        desc = numeric_df.describe().T  # .T (transpose): columns become rows, stats become columns
        desc["skew"] = numeric_df.skew()
        desc["missing"] = numeric_df.isna().sum()
        table = _df_to_markdown_table(desc.round(2).reset_index(names="column"))
        self.sections["numeric"] = f"## Numeric summary\n\n{table}\n"

    def _profile_categorical(self) -> None:
        cat_df = self.df.select_dtypes(include=["object", "category"])
        if cat_df.empty:
            self.sections["categorical"] = "## Categorical summary\n\nNo text/categorical columns.\n"
            return
        blocks = []
        for col in cat_df.columns:
            top = cat_df[col].value_counts().head(8)
            lines = "\n".join(f"  - {v}: {n:,}" for v, n in top.items())
            blocks.append(f"**{col}** ({cat_df[col].nunique()} unique values)\n\n{lines}")
        self.sections["categorical"] = "## Categorical summary\n\n" + "\n\n".join(blocks) + "\n"
    
        
    def _profile_bivariate(self) -> None:
        numeric_only = self.df.select_dtypes(include="number")
        numeric_df = numeric_only.drop(columns=self.exclude_columns, errors="ignore")
        if numeric_df.shape[1] < 2:
            self.sections["bivariate"] = "## Bivariate summary\n\nNot enough numeric columns to compute correlations.\n"
            return
        results = []
        for col_a, col_b in it.combinations(numeric_df.columns, 2):
            pair = numeric_df[[col_a, col_b]].dropna()
            if len(pair) < 3:
                results.append((col_a, col_b, None, None, None))
                continue
            r, p = stats.pearsonr(pair[col_a], pair[col_b])
            dof = len(pair) - 2
            results.append((col_a, col_b, r, dof, p))
        bivariate_df = pd.DataFrame(results, columns=["col_a", "col_b", "pearson_r", "dof", "p_value"])
        table = _df_to_markdown_table(bivariate_df.round(4))
        self.sections["bivariate"] = f"## Bivariate summary\n\n{table}\n"

    def _profile_categorical_bivariate(self) -> None:
        cat_df = self.df.select_dtypes(include=["object", "category"])
        cat_df = cat_df.drop(columns=self.exclude_columns, errors="ignore")
        results = []
        counts = cat_df.nunique()
        counts = counts[counts > 1]  # keep only columns with more than one unique value
        cat_cols = counts.index
        numeric_cols = self.df.select_dtypes(include='number').columns
        if len(cat_cols) < 1 or len(numeric_cols) < 1:
                    self.sections["categorical_bivariate"] = "## Categorical bivariate summary\n\nNot enough categorical columns to compute associations.\n"
                    return
        for col_a, col_b in it.product(cat_cols, numeric_cols):
            enough_categories = self.df[col_a].value_counts() >= self.min_category_size
            categories_valid = enough_categories[enough_categories].index
            categories_verified = self.df[col_a].isin(categories_valid)
            categories_passed = len(self.df[categories_verified]) >0
             # groupby produces a Series: index = group value, value = mean
            grp_series = self.df[categories_verified].groupby(col_a)[col_b].agg(["mean", "sum"])

        # iterate (group_value, mean_val) pairs and append one row per group
            if categories_passed: 
                for group_val, row in grp_series.iterrows():
                    results.append({
                    "cat_col": col_a,
                    "num_col": col_b,
                    "group": group_val,
                    "mean": row['mean'],
                    "sum": row['sum']
            })
            else: 
                results.append({
                "cat_col": col_a,
                "num_col": col_b,
                "group": "not enough categories",
                "mean": None,
                "sum": None
            })
        bivariate_cat_df = pd.DataFrame(results)
        table = _df_to_markdown_table(bivariate_cat_df.round(4))
        self.sections["categorical_bivariate"] = f"## Categorical bivariate summary\n\n{table}\n"

   
    def _profile_grouped(self) -> None:
        named_cols = {"group": self.group, "metric": self.metric, "percent": self.percent}

        missing = [name for name, col in named_cols.items() if col is None]
        nobody_tried = len(missing) == len(named_cols)
        if nobody_tried:
            self.sections["grouped"] = "## Grouped summary\n\nNo grouping requested.\n"
            return
        not_found = [name for name, col in named_cols.items() if col is not None and col not in self.df.columns]

        has_percent_cols = not missing and not not_found
        has_n = self.n is not None and self.n in self.df.columns
        has_n_and_overall = has_n and self.is_overall is not None and self.is_overall in self.df.columns

        if not has_percent_cols:
            # build the message from `missing` and `not_found`
            parts = []
            if missing:
                parts.append(f"Missing required columns: {', '.join(missing)}")
                       
            if not_found:
                parts.append(f"Columns not found in DataFrame: {', '.join(not_found)}")
            self.sections["grouped"] = "## Grouped summary\n\n" + "; ".join(parts) + "\n"
        else:
            # has_percent_cols is guaranteed True here — safe to compute once
            wide = self.df.pivot(index=self.group, columns=self.metric, values=self.percent)
            table = _df_to_markdown_table(wide.reset_index(names=self.group))

            if not has_n:
                # branch 2, reuses wide/table, just its own message
                self.sections["grouped"] = (
                    f"## Grouped summary\n\n{table}\n\n"
                    "`n` pivot table but chi square test unavailable.\n"
                )
  
            elif not has_n_and_overall:
            # branch 3, reuses wide/table, just its own message
                self.sections["grouped"] = (
                    f"## Grouped summary\n\n{table}\n\n"
                    "`n` and `chi-square includes is_overall. p=value is meaningless`.\n"
                )
            else:
                blocks = []  # outside outer loop — survives across metrics
                for metric_value in self.df[self.metric].unique():
                    rows = []  # inside outer loop — fresh per metric
                    subset = self.df[self.df[self.metric] == metric_value]
                    subset = subset[subset[self.is_overall] != self.is_overall_value]
                    generation_counts = {}
                    for index, row in subset.iterrows():
                        yes = round(row[self.percent] * row[self.n] / 100)
                        no = round(row[self.n] - yes)
                        generation_counts[row[self.group]] = [yes, no]
                    # after building generation_counts (done via for index,row in subset.iterrows()):
                    chi2, p, dof, expected = stats.chi2_contingency(list(generation_counts.values()))

                    # compute column totals (Yes, No) and grand total — must be after generation_counts built
                    col_totals = [sum(col) for col in zip(*generation_counts.values())]    # -> [total_yes, total_no]
                    grand_total = sum(sum(pair) for pair in generation_counts.values())    # -> total respondents
                    
                    for name, counts, exp in zip(generation_counts.keys(), generation_counts.values(), expected):
                        
                        
                        row_total = sum(counts)

                        correction_yes = (1 - row_total / grand_total) * (1 - col_totals[0] / grand_total)
                        residual_yes = (counts[0] - exp[0]) / (exp[0] * correction_yes) ** 0.5

                        correction_no = (1 - row_total / grand_total) * (1 - col_totals[1] / grand_total)
                        residual_no = (counts[1] - exp[1]) / (exp[1] * correction_no) ** 0.5
                        
                        rows.append(f"| {name} | {counts[0]} | {exp[0]:.2f} | {counts[1]} | {exp[1]:.2f} | {residual_yes:.2f} | {residual_no:.2f} |")

                    header = "| Generation | Observed Yes | Expected Yes | Observed No | Expected No | Residual Yes | Residual No |"
                    divider = "|---|---:|---:|---:|---:|---:|---:|"
                    table = "\n".join([header, divider] + rows)

                    block = f"### {metric_value}\n\np-value: {p:.4g}\n\n" + table
                    blocks.append(block)

                self.sections["grouped"] = "## Grouped summary\n\n" + "\n\n".join(blocks)
                
    def _profile_categorical_categorical(self) -> None:
        cat_df = self.df.select_dtypes(include=["object", "category"])
        cat_df = cat_df.drop(columns=self.exclude_columns, errors="ignore")
        results = []
        counts = cat_df.nunique()
        counts = counts[counts > 1]  # keep only columns with more than one unique value
        cat_cols = counts.index
        if len(cat_cols) < 2:
                        self.sections["cat_cat"] = "## Chi square contingent\n\nNot enough categorical columns to compute associations.\n"
                        return
        for col_a, col_b in it.combinations(cat_cols, 2):
            valid_categories_a = self.df[col_a].value_counts()>=self.min_category_size
            valid_categories_b = self.df[col_b].value_counts()>=self.min_category_size
            verified_categories_a = valid_categories_a[valid_categories_a].index
            verified_categories_b = valid_categories_b[valid_categories_b].index
            column_threshold = self.df[col_a].isin(verified_categories_a) & self.df[col_b].isin(verified_categories_b)
            threshold_passed = len(self.df[column_threshold]) > 0
            if threshold_passed:
                crosstab_table = pd.crosstab(self.df[column_threshold][col_a], self.df[column_threshold][col_b])
                chi2, p, dof, expected = stats.chi2_contingency(crosstab_table)
                categories_passed = np.all(expected>=5)
                if categories_passed:
                    results.append({
                        "cat_col_a": col_a,
                        "cat_col_b": col_b,
                        "chi2": chi2,
                        "p_value" : p,
                        "dof":dof,
                        "note": "categories passed"
                            })
                else:
                    results.append({
                    "cat_col_a": col_a,
                    "cat_col_b": col_b,
                    "chi2": None,
                    "p_value" : None,
                    "dof":None,
                    "note": "not enough expected observations"
                })
            else:
                results.append({
                "cat_col_a": col_a,
                "cat_col_b": col_b,
                "chi2": None,
                "p_value" : None,
                "dof":None,
                "note": "not enough categories"
            })
        cat_cat_df = pd.DataFrame(results)
        table = _df_to_markdown_table(cat_cat_df.round(4))
        self.sections["cat_cat"] = f"## Cat_Cat summary\n\n{table}\n"           
                    
                
                
                
    def _profile_ols(self) -> None:
        cat_df = self.df.select_dtypes(include=["object", "category"])
        cat_df = cat_df.drop(columns=self.exclude_columns, errors="ignore")
        results = []
        coef_results = []
        counts = cat_df.nunique()
        counts = counts[counts > 1]  # keep only columns with more than one unique value
        cat_cols = counts.index
        numeric_df = self.df.select_dtypes(include='number')
        numeric_df = numeric_df.drop(columns=self.exclude_columns, errors="ignore")
        numeric_cols = numeric_df.columns
        if len(cat_cols) < 1 or len(numeric_cols) < 1:
                self.sections["ols"] = "## OLS regression summary\n\nNot enough categorical columns to compute associations.\n"
                return

        
        for col_a, col_b in it.product(cat_cols, numeric_cols):
            valid_categories = self.df[col_a].value_counts()>=self.min_category_size
            verified_categories = valid_categories[valid_categories].index
            big_enough = self.df[col_a].isin(verified_categories)
            categories_passed= len(self.df[big_enough]) > 0
            if categories_passed:
                model = smf.ols(f"{col_b} ~ {col_a}", data=self.df[big_enough]).fit() 
                results.append({
                "cat_col": col_a,
                "num_col": col_b,
                "r_squared": model.rsquared,
                "f_stat" : model.fvalue,
                "p_value": model.f_pvalue
            })
                for term, coefficient in model.params.items():
                    coef_results.append({
                    "cat_col": col_a,
                    "num_col": col_b,
                    "term": term,
                    "coefficient": coefficient  
                            })
            else:
               results.append({
                    "cat_col": col_a,
                    "num_col": col_b,
                    "r_squared": "not enough categories",
                    "f_stat" : None,
                    "p_value": None
                           }) 
            
            
        ols_cat_df = pd.DataFrame(results)
        table = _df_to_markdown_table(ols_cat_df.round(4))
        self.sections["ols"] = f"## OLS summary\n\n{table}\n"
        
        ols_coeff_df = pd.DataFrame(coef_results)
        table = _df_to_markdown_table(ols_coeff_df.round(4))
        self.sections["ols_coefficients"] = f"## OLS Coefficients summary\n\n{table}\n"
     
        
          

def _df_to_markdown_table(df: pd.DataFrame) -> str:
    """Render a DataFrame as a GitHub-flavored Markdown table, no extra deps.

    (pandas' own .to_markdown() needs the optional `tabulate` package —
    writing 6 lines here avoids adding a dependency for one method.)
    """
    cols = list(df.columns)
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    divider = "| " + " | ".join("---" for _ in cols) + " |"
    rows = [
        "| " + " | ".join(str(v) for v in row) + " |"
        for row in df.itertuples(index=False)
    ]
    return "\n".join([header, divider, *rows])
