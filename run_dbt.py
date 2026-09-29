"""Roda o dbt usando a mesma DATABASE_URL do .env (sem duplicar a senha em outro arquivo).

Uso: python run_dbt.py build      (ou: debug, run, test, docs generate)
"""
import os
import sys
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv
from dbt.cli.main import dbtRunner

load_dotenv()
url = urlparse(os.environ["DATABASE_URL"])
os.environ.update({
    "DBT_HOST": url.hostname,
    "DBT_PORT": str(url.port or 5432),
    "DBT_USER": unquote(url.username),
    "DBT_PASSWORD": unquote(url.password),
    "DBT_DBNAME": url.path.lstrip("/") or "postgres",
})
args = sys.argv[1:] or ["build"]
resultado = dbtRunner().invoke(args + ["--project-dir", "dbt", "--profiles-dir", "dbt"])
sys.exit(0 if resultado.success else 1)
