"""Roda o dbt usando a mesma DATABASE_URL do .env (sem duplicar a senha em outro arquivo).

Uso: python run_dbt.py build                      (Supabase/PostgreSQL)
     python run_dbt.py build --target bigquery    (BigQuery; chave em ~/.gcp/dbt-bigquery.json)
"""
import json
import os
import sys
from pathlib import Path
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
chave = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", str(Path.home() / ".gcp" / "dbt-bigquery.json"))
if os.path.exists(chave):
    os.environ["DBT_BQ_KEYFILE"] = chave
    os.environ["DBT_BQ_PROJECT"] = json.load(open(chave, encoding="utf-8"))["project_id"]
args = sys.argv[1:] or ["build"]
resultado = dbtRunner().invoke(args + ["--project-dir", "dbt", "--profiles-dir", "dbt"])
sys.exit(0 if resultado.success else 1)
