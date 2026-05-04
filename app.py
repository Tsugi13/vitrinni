"""
app.py
------
Flask backend for Vitrinni.
Serves HTML pages and provides API endpoints for login/signup.
Run with: python app.py
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import sqlite3
from datetime import datetime
from functions import (
    init_users_db, init_stores_db,
    user_signup, user_login,
    _hash_password, _get_conn,
    STORES_DB, seed_stores
)

app = Flask(__name__, template_folder="templates")
app.secret_key = "vitrinni-secret-key-2024"

# Inicialização dos BDs
init_users_db()
init_stores_db()
seed_stores()  # Popula o BD de lojas com dados iniciais (se vazio)

# Rotas para páginas HTML

@app.route("/")
@app.route("/main.html")
def index():
    return render_template("main.html", user=session.get("user"))

@app.route("/login.html")
def login_page():
    if session.get("user"):
        return redirect(url_for("index"))
    return render_template("login.html", user=None)

@app.route("/cadastro.html")
def cadastro_page():
    if session.get("user"):
        return redirect(url_for("index"))
    return render_template("cadastro.html", user=None)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# Rotas de APIs para login/cadastro

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    result = user_login(
        email=data.get("email", ""),
        password=data.get("password", ""),
    )
    if result["success"]:
        session["user"] = result["user"]
    return jsonify(result), 200 if result["success"] else 401


@app.route("/api/signup", methods=["POST"])
def api_signup():
    data = request.get_json(silent=True) or {}
    result = user_signup(
        name=data.get("name", ""),
        email=data.get("email", ""),
        phone=data.get("phone", ""),
        password=data.get("password", ""),
    )
    if result["success"]:
        # auto-login after sign-up
        login_result = user_login(data.get("email", ""), data.get("password", ""))
        if login_result["success"]:
            session["user"] = login_result["user"]
    return jsonify(result), 201 if result["success"] else 400


@app.route("/api/session")
def api_session():
    return jsonify({"user": session.get("user")})


@app.route("/api/products")
def api_products():
    """Return all products with their store name, price and stock."""
    from functions import list_all_products
    result = list_all_products()
    return jsonify(result)


@app.route("/loja.html")
def loja_page():
    return render_template("loja.html", user=session.get("user"))


@app.route("/finalizar.html")
def finalizar_page():
    return render_template("finalizar.html", user=session.get("user"))


# Inicialização do site

if __name__ == "__main__":
    print("\n  Vitrinni rodando em http://127.0.0.1:5000\n")
    app.run(debug=True)
