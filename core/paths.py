import os
import sys


def get_runtime_root():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_bundle_root():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return get_runtime_root()


def runtime_path(*parts):
    return os.path.join(get_runtime_root(), *parts)


def bundle_path(*parts):
    return os.path.join(get_bundle_root(), *parts)
