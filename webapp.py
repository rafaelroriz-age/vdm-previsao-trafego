"""
webapp.py
---------
Servidor local para o novo layout com API de configuração/execução do pipeline.

Executar:
  python webapp.py

Abrir:
  http://localhost:8777
"""
from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

import config as cfg
from src.runtime_pipeline import build_candidates, default_runtime_config, run_pipeline_runtime

app = Flask(__name__, static_folder=str(cfg.BASE_DIR / "docs"), static_url_path="")
UPLOAD_DIR = cfg.BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/config/default")
def api_default_config():
    return jsonify(default_runtime_config())


@app.get("/api/options")
def api_options():
    cfg0 = default_runtime_config()
    cands = build_candidates(cfg0)
    return jsonify({"default": cfg0, "options": cands})


@app.get("/api/health")
def api_health():
    return jsonify({"ok": True, "status": "healthy"})


@app.post("/api/candidates")
def api_candidates():
    payload = request.get_json(silent=True) or {}
    cands = build_candidates(payload)
    return jsonify(cands)


@app.post("/api/run")
def api_run():
    payload = request.get_json(silent=True) or {}
    result = run_pipeline_runtime(payload)
    return jsonify(result)


@app.post("/api/upload")
def api_upload():
    f = request.files.get("file")
    if f is None or not f.filename:
        return jsonify({"ok": False, "error": "Arquivo não enviado"}), 400
    name = Path(f.filename).name
    ext = Path(name).suffix.lower()
    if ext not in {".xlsx", ".xls", ".csv"}:
        return jsonify({"ok": False, "error": "Formato inválido. Use .xlsx, .xls ou .csv"}), 400
    dst = UPLOAD_DIR / name
    f.save(dst)
    rel = dst.relative_to(cfg.BASE_DIR).as_posix()
    return jsonify({"ok": True, "dataset_path": rel, "filename": name})


@app.errorhandler(Exception)
def on_error(err):
    return jsonify({"ok": False, "error": str(err)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8777, debug=False)
