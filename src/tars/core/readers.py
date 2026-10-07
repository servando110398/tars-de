import io
import dlt
import pandas as pd                                                                                                                                                                                            

def _as_file_items(items):
    """Accept a single file item or a page (list) of them, so both load commands work."""
    return items if isinstance(items, list) else [items]


def _with_text_hints(df: pd.DataFrame):
    """Turn NaN into real nulls and mark every column as nullable text."""
    df = df.astype(object).where(df.notna(), None)
    columns = [{"name": col, "data_type": "text", "nullable": True} for col in df.columns]
    return dlt.mark.with_hints(
        df.to_dict(orient="records"),
        dlt.mark.make_hints(columns=columns),
    )


@dlt.transformer
def read_excel(items):
    for file_obj in _as_file_items(items):
        with file_obj.open() as file:
            df = pd.read_excel(file, dtype=str, keep_default_na=False, na_values=[""])
        yield _with_text_hints(df)


@dlt.transformer
def read_csv(items, encoding: str = "utf-8", sep: str = ","):
    for file_obj in _as_file_items(items):
        with file_obj.open() as file:
            raw = file.read()
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            text = raw.decode("cp1252")  # common for files exported from Windows tools
        df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False, na_values=[""], sep=sep)
        yield _with_text_hints(df)
