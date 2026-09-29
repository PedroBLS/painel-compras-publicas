"""Ponto de entrada no AWS Lambda: roda a carga incremental do etl.py (agendada todo dia pelo EventBridge)."""
import etl


def lambda_handler(event, context):
    etl.main([])  # sem argumentos = continua do último dia carregado até hoje
    return {"ok": True}
