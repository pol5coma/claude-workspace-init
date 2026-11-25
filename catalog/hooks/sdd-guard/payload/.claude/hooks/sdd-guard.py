"""Native SDD hook entrypoint; installed with the SPADO interpreter."""
from pathlib import Path
import argparse
from spado.sdd.hooks import main

parser = argparse.ArgumentParser()
parser.add_argument("--host", choices=["claude", "codex"], required=True)
args = parser.parse_args()
main(Path(__file__).resolve().parents[2], args.host)
