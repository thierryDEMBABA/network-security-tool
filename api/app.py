import os
import socket
import time

import psycopg
from flask import Flask, jsonify

app = Flask(__name__)

DATABASE_URL = (
    f"host={os.environ.get('DB_HOST', 'db')} "
    f"port={os.environ.get('DB_PORT', '5432')} "
    f"dbname={os.environ['POSTGRES_DB']} "
    f"user={os.environ['POSTGRES_USER']} "
    f"password={os.environ['POSTGRES_PASSWORD']}"
)


def parse_targets(raw):
    # Format : "nom=hote:port,nom=hote:port"
    targets = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        name, address = item.split("=", 1)
        host, port = address.rsplit(":", 1)
        targets.append({"name": name, "host": host, "port": int(port)})
    return targets


# Liste fermée de cibles : l'API ne peut pas servir de scanner de ports arbitraire.
TARGETS = parse_targets(os.environ.get("TARGETS", "api=api:5000,db=db:5432,frontend=frontend:80"))


def is_valid_port(port):
    return isinstance(port, int) and 1 <= port <= 65535


def check_port(host, port, timeout=2):
    if not is_valid_port(port):
        raise ValueError("Invalid port")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        try:
            return sock.connect_ex((host, port)) == 0
        except socket.gaierror:
            return False


def get_conn():
    return psycopg.connect(DATABASE_URL, connect_timeout=3)


def init_db(retries=10, delay=2):
    for attempt in range(1, retries + 1):
        try:
            with get_conn() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS checks (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        host TEXT NOT NULL,
                        port INTEGER NOT NULL,
                        is_open BOOLEAN NOT NULL,
                        checked_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
            return
        except psycopg.OperationalError:
            if attempt == retries:
                raise
            time.sleep(delay)


@app.get("/api/health")
def health():
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
        db_status = "up"
    except psycopg.Error:
        db_status = "down"
    status = 200 if db_status == "up" else 503
    return jsonify(status="ok" if status == 200 else "degraded", database=db_status), status


@app.get("/api/targets")
def targets():
    return jsonify(TARGETS)


@app.post("/api/checks")
def run_checks():
    results = []
    with get_conn() as conn:
        for target in TARGETS:
            is_open = check_port(target["host"], target["port"])
            row = conn.execute(
                "INSERT INTO checks (name, host, port, is_open) VALUES (%s, %s, %s, %s) "
                "RETURNING checked_at",
                (target["name"], target["host"], target["port"], is_open),
            ).fetchone()
            results.append({**target, "is_open": is_open, "checked_at": row[0].isoformat()})
    return jsonify(results), 201


@app.get("/api/checks")
def list_checks():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT name, host, port, is_open, checked_at FROM checks "
            "ORDER BY checked_at DESC LIMIT 20"
        ).fetchall()
    return jsonify(
        [
            {"name": r[0], "host": r[1], "port": r[2], "is_open": r[3], "checked_at": r[4].isoformat()}
            for r in rows
        ]
    )


init_db()
