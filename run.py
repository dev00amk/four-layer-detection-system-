"""Compatibility shim: the pipeline CLI lives in sentinel.cli.

Kept so `python run.py <command>` (README, CI, docs) keeps working alongside
the installed `sentinel` entry point.
"""
from sentinel.cli import main

if __name__ == "__main__":
    main()
