"""Gera lambda.zip com o código e as dependências compiladas para o Linux do Lambda (Python 3.12, x86_64).

Uso: python build_lambda.py
"""
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PASTA = Path("build/lambda")
ARQUIVOS = ["lambda_function.py", "etl.py", "schema.sql"]

shutil.rmtree(PASTA, ignore_errors=True)
subprocess.run([
    sys.executable, "-m", "pip", "install", "--quiet", "--target", str(PASTA),
    "--platform", "manylinux2014_x86_64", "--python-version", "3.12", "--only-binary=:all:",
    "requests", "psycopg[binary]", "python-dotenv",
    "typing-extensions",  # o pip roda no Python local e pula essa dependência que o 3.12 exige
], check=True)
for a in ARQUIVOS:
    shutil.copy(a, PASTA)

with zipfile.ZipFile("lambda.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in PASTA.rglob("*"):
        if "__pycache__" not in f.parts:
            z.write(f, f.relative_to(PASTA))
print(f"lambda.zip: {Path('lambda.zip').stat().st_size / 1e6:.1f} MB")
