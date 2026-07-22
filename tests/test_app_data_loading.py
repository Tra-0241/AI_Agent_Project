import importlib
import sys
import types
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class _DummyContainer:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyStreamlit(types.ModuleType):
    def __init__(self, name: str = "streamlit") -> None:
        super().__init__(name)
        self.session_state = {}

    def __getattr__(self, name):
        if name == "cache_data":
            return lambda func=None, **kwargs: (func if func is not None else (lambda f: f))
        if name == "sidebar":
            return _DummyStreamlit("streamlit.sidebar")
        if name == "columns":
            def _columns(*args, **kwargs):
                if args:
                    if isinstance(args[0], int):
                        return [_DummyContainer() for _ in range(args[0])]
                    if isinstance(args[0], list):
                        return [_DummyContainer() for _ in args[0]]
                return []

            return _columns
        if name == "tabs":
            return lambda *args, **kwargs: tuple(_DummyContainer() for _ in args[0])
        if name == "container":
            return lambda *args, **kwargs: _DummyContainer()
        if name == "expander":
            return lambda *args, **kwargs: _DummyContainer()
        if name == "set_page_config":
            return lambda *args, **kwargs: None
        if name == "markdown":
            return lambda *args, **kwargs: None
        if name == "plotly_chart":
            return lambda *args, **kwargs: None
        if name == "info":
            return lambda *args, **kwargs: None
        if name == "success":
            return lambda *args, **kwargs: None
        if name == "caption":
            return lambda *args, **kwargs: None
        if name == "error":
            return lambda *args, **kwargs: None
        if name == "stop":
            return lambda *args, **kwargs: None
        if name == "button":
            return lambda *args, **kwargs: False
        if name == "selectbox":
            return lambda *args, **kwargs: args[1][0] if args and len(args) > 1 else None
        if name == "multiselect":
            return lambda *args, **kwargs: []
        if name == "slider":
            return lambda *args, **kwargs: (args[1], args[2]) if len(args) > 2 else (0, 1)
        if name == "text_input":
            return lambda *args, **kwargs: ""
        if name == "empty":
            return lambda *args, **kwargs: _DummyContainer()
        return lambda *args, **kwargs: None


def test_read_processed_csv_repairs_mojibake_columns(tmp_path) -> None:
    dummy_streamlit = _DummyStreamlit("streamlit")
    sys.modules["streamlit"] = dummy_streamlit

    app_module = importlib.import_module("app.app")

    csv_path = tmp_path / "friction.csv"
    pd.DataFrame({"Task ID": [1], "LÃ½ do chÃ­nh": ["A"]}).to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig",
    )

    result = app_module.read_processed_csv(csv_path)

    assert "Lý do chính" in result.columns
    assert result.loc[0, "Lý do chính"] == "A"
