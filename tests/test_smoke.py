from importlib import import_module


def test_package_imports() -> None:
    module = import_module("kreo_kontrol")
    assert module.__name__ == "kreo_kontrol"

