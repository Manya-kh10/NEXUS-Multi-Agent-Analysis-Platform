import pandas as pd
import numpy as np


class CleaningPipeline:

    # Max rows to sample when probing column dtypes
    _DTYPE_SAMPLE_SIZE = 100

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.report = []

    def drop_duplicates(self):
        before = len(self.df)
        self.df.drop_duplicates(inplace=True)
        removed = before - len(self.df)
        self.report.append({"step": "drop_duplicates", "removed_rows": removed})
        return self

    def handle_missing(self, strategy: str = "auto"):
        cols_to_drop = []
        for col in self.df.columns:
            missing = self.df[col].isnull().sum()
            if missing == 0:
                continue
            pct = missing / len(self.df)

            if pct > 0.6:
                cols_to_drop.append(col)
                self.report.append({"step": "drop_column", "column": col, "missing_pct": round(pct, 2)})
            elif self.df[col].dtype in [np.float64, np.int64]:
                median_val = self.df[col].median()
                self.df[col] = self.df[col].fillna(median_val)
                self.report.append({"step": "fill_median", "column": col})
            else:
                mode_val = self.df[col].mode()
                if len(mode_val) > 0:
                    self.df[col] = self.df[col].fillna(mode_val.iloc[0])
                self.report.append({"step": "fill_mode", "column": col})

        if cols_to_drop:
            self.df.drop(columns=cols_to_drop, inplace=True)
        return self

    def fix_dtypes(self):
        """Probe a small sample before attempting expensive full-column casts.

        For every object column, try to_datetime and to_numeric on a 100-row
        sample first.  Only cast the entire column when the sample succeeds.
        This turns O(N*C) exception-heavy work into O(100*C) for columns that
        will never convert, which is the common case.
        """
        obj_cols = list(self.df.select_dtypes(include="object").columns)
        sample_n = min(self._DTYPE_SAMPLE_SIZE, len(self.df))

        for col in obj_cols:
            sample = self.df[col].dropna().head(sample_n)
            if sample.empty:
                continue

            # ---- Try datetime on sample first --------------------------------
            try:
                pd.to_datetime(sample, infer_datetime_format=True)
                # Sample passed – cast full column (errors → NaT kept as-is)
                self.df[col] = pd.to_datetime(self.df[col], errors="coerce")
                self.report.append({"step": "cast_datetime", "column": col})
                continue
            except Exception:
                pass

            # ---- Try numeric on sample first ---------------------------------
            try:
                pd.to_numeric(sample)
                self.df[col] = pd.to_numeric(self.df[col], errors="coerce")
                self.report.append({"step": "cast_numeric", "column": col})
            except Exception:
                pass

        return self

    def remove_outliers(self):
        """Vectorised outlier removal: accumulate a single boolean mask across
        all numeric columns instead of filtering the DataFrame column-by-column
        (which copies the full frame each iteration).
        """
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) == 0:
            return self

        mask = pd.Series(True, index=self.df.index)
        for col in numeric_cols:
            Q1 = self.df[col].quantile(0.25)
            Q3 = self.df[col].quantile(0.75)
            IQR = Q3 - Q1
            col_mask = (self.df[col] >= Q1 - 1.5 * IQR) & (self.df[col] <= Q3 + 1.5 * IQR)
            removed = (~col_mask & mask).sum()
            mask &= col_mask
            if removed > 0:
                self.report.append({"step": "remove_outliers", "column": col, "removed_rows": int(removed)})

        before = len(self.df)
        self.df = self.df[mask]
        total_removed = before - len(self.df)
        if total_removed > 0 and not any(r["step"] == "remove_outliers" for r in self.report):
            self.report.append({"step": "remove_outliers", "removed_rows": total_removed})
        return self

    def standardize_strings(self):
        str_cols = self.df.select_dtypes(include="object").columns
        if len(str_cols) > 0:
            self.df[str_cols] = self.df[str_cols].apply(
                lambda s: s.str.strip().str.lower()
            )
            for col in str_cols:
                self.report.append({"step": "standardize_strings", "column": col})
        return self

    def run_all(self):
        return (
            self
            .drop_duplicates()
            .handle_missing()
            .fix_dtypes()
            .remove_outliers()
            .standardize_strings()
        )

    def save(self, output_path: str):
        self.df.to_csv(output_path, index=False)
        return {"rows": len(self.df), "columns": len(self.df.columns), "report": self.report}