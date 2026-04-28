# Lógica do backend para o sistema de gerenciamento de lojas e produtos.
# Usa SQLite para persistência, com tabelas para usuários, lojas, produtos e inventário.
# Fornece funções para cadastro/login de usuários e lojas, busca de lojas, adição de produtos e atualização de estoque.

import sqlite3
import hashlib
import os
import json
import re
from datetime import datetime


# CONFIG

USERS_DB  = "users.db"
STORES_DB = "stores.db"


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def _hash_password(password: str) -> str:
    """SHA-256 hash with a random salt, stored as salt$hash."""
    salt = os.urandom(16).hex()
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hashed}"


def _verify_password(password: str, stored: str) -> bool:
    """Re-hash with the stored salt and compare."""
    salt, hashed = stored.split("$", 1)
    return hashlib.sha256((salt + password).encode()).hexdigest() == hashed


def _is_valid_email(email: str) -> bool:
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))


def _get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row          # lets us access columns by name
    conn.execute("PRAGMA journal_mode=WAL") # safer concurrent writes
    return conn


# ──────────────────────────────────────────────
# DATABASE INITIALISATION
# ──────────────────────────────────────────────

def init_users_db():
    """
    Create the users table if it doesn't exist yet.

    Schema
    ------
    id          INTEGER  – auto-increment primary key
    name        TEXT     – full name
    email       TEXT     – unique login identifier
    phone       TEXT     – contact number
    password    TEXT     – salt$sha256 hash
    created_at  TEXT     – ISO-8601 timestamp
    """
    with _get_conn(USERS_DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT    NOT NULL,
                email      TEXT    NOT NULL UNIQUE,
                phone      TEXT    NOT NULL,
                password   TEXT    NOT NULL,
                created_at TEXT    NOT NULL
            )
        """)
        conn.commit()


def init_stores_db():
    """
    Create the stores, products, and inventory tables if they don't exist.

    stores
    ------
    id           INTEGER – PK
    store_name   TEXT    – public name of the store
    owner_name   TEXT    – legal owner name
    phone        TEXT
    email        TEXT    – unique login identifier
    password     TEXT    – salt$sha256 hash
    created_at   TEXT

    products
    --------
    id           INTEGER – PK
    store_id     INTEGER – FK → stores.id
    name         TEXT    – product name
    description  TEXT
    price        REAL
    created_at   TEXT

    inventory
    ---------
    id           INTEGER – PK
    product_id   INTEGER – FK → products.id
    store_id     INTEGER – FK → stores.id  (denormalised for fast queries)
    quantity     INTEGER
    updated_at   TEXT
    """
    with _get_conn(STORES_DB) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS stores (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                store_name  TEXT    NOT NULL,
                owner_name  TEXT    NOT NULL,
                phone       TEXT    NOT NULL,
                email       TEXT    NOT NULL UNIQUE,
                password    TEXT    NOT NULL,
                created_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS products (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id    INTEGER NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
                name        TEXT    NOT NULL,
                description TEXT    DEFAULT '',
                price       REAL    NOT NULL DEFAULT 0.0,
                created_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS inventory (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                store_id    INTEGER NOT NULL REFERENCES stores(id)  ON DELETE CASCADE,
                quantity    INTEGER NOT NULL DEFAULT 0,
                updated_at  TEXT    NOT NULL
            );
        """)
        conn.commit()


# ──────────────────────────────────────────────
# USER  –  SIGN-UP & LOGIN
# ──────────────────────────────────────────────

def user_signup(name: str, email: str, phone: str, password: str) -> dict:
    """
    Register a new customer account.

    Returns
    -------
    {"success": True,  "user_id": <int>}
    {"success": False, "error":   <str>}
    """
    # ── validation ──
    if not all([name, email, phone, password]):
        return {"success": False, "error": "All fields are required."}
    if not _is_valid_email(email):
        return {"success": False, "error": "Invalid e-mail format."}
    if len(password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters."}

    hashed = _hash_password(password)
    now    = datetime.utcnow().isoformat()

    try:
        with _get_conn(USERS_DB) as conn:
            cursor = conn.execute(
                "INSERT INTO users (name, email, phone, password, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (name.strip(), email.lower().strip(), phone.strip(), hashed, now)
            )
            conn.commit()
            return {"success": True, "user_id": cursor.lastrowid}

    except sqlite3.IntegrityError:
        return {"success": False, "error": "E-mail already registered."}
    except Exception as e:
        return {"success": False, "error": f"Database error: {e}"}


def user_login(email: str, password: str) -> dict:
    """
    Authenticate a customer.

    Returns
    -------
    {"success": True,  "user": {"id", "name", "email", "phone"}}
    {"success": False, "error": <str>}
    """
    if not email or not password:
        return {"success": False, "error": "E-mail and password are required."}

    with _get_conn(USERS_DB) as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
        ).fetchone()

    if not row or not _verify_password(password, row["password"]):
        return {"success": False, "error": "Invalid e-mail or password."}

    return {
        "success": True,
        "user": {
            "id":    row["id"],
            "name":  row["name"],
            "email": row["email"],
            "phone": row["phone"],
        }
    }


# ──────────────────────────────────────────────
# STORE  –  SIGN-UP & LOGIN
# ──────────────────────────────────────────────

def store_signup(store_name: str, owner_name: str,
                 phone: str, email: str, password: str) -> dict:
    """
    Register a new store account.
    Products / inventory are NOT required at sign-up.

    Returns
    -------
    {"success": True,  "store_id": <int>}
    {"success": False, "error":    <str>}
    """
    if not all([store_name, owner_name, phone, email, password]):
        return {"success": False, "error": "All fields are required."}
    if not _is_valid_email(email):
        return {"success": False, "error": "Invalid e-mail format."}
    if len(password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters."}

    hashed = _hash_password(password)
    now    = datetime.utcnow().isoformat()

    try:
        with _get_conn(STORES_DB) as conn:
            cursor = conn.execute(
                "INSERT INTO stores (store_name, owner_name, phone, email, password, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (store_name.strip(), owner_name.strip(),
                 phone.strip(), email.lower().strip(), hashed, now)
            )
            conn.commit()
            return {"success": True, "store_id": cursor.lastrowid}

    except sqlite3.IntegrityError:
        return {"success": False, "error": "E-mail already registered."}
    except Exception as e:
        return {"success": False, "error": f"Database error: {e}"}


def store_login(email: str, password: str) -> dict:
    """
    Authenticate a store owner.

    Returns
    -------
    {"success": True,  "store": {"id", "store_name", "owner_name", "email", "phone"}}
    {"success": False, "error": <str>}
    """
    if not email or not password:
        return {"success": False, "error": "E-mail and password are required."}

    with _get_conn(STORES_DB) as conn:
        row = conn.execute(
            "SELECT * FROM stores WHERE email = ?", (email.lower().strip(),)
        ).fetchone()

    if not row or not _verify_password(password, row["password"]):
        return {"success": False, "error": "Invalid e-mail or password."}

    return {
        "success": True,
        "store": {
            "id":         row["id"],
            "store_name": row["store_name"],
            "owner_name": row["owner_name"],
            "email":      row["email"],
            "phone":      row["phone"],
        }
    }


# ──────────────────────────────────────────────
# STORES  –  SEARCH BY NAME
# ──────────────────────────────────────────────

def search_stores(name: str) -> dict:
    """
    Find stores whose name contains the search term (case-insensitive).

    Returns
    -------
    {"success": True,  "stores": [{"id", "store_name", "owner_name", "phone", "email"}, ...]}
    {"success": False, "error":  <str>}
    """
    if not name:
        return {"success": False, "error": "Search term is required."}

    try:
        with _get_conn(STORES_DB) as conn:
            rows = conn.execute(
                "SELECT id, store_name, owner_name, phone, email "
                "FROM stores WHERE store_name LIKE ? ORDER BY store_name",
                (f"%{name.strip()}%",)
            ).fetchall()

        return {"success": True, "stores": [dict(r) for r in rows]}

    except Exception as e:
        return {"success": False, "error": f"Database error: {e}"}


# ──────────────────────────────────────────────
# PRODUCTS  –  ADD / LIST
# ──────────────────────────────────────────────

def add_product(store_id: int, name: str,
                description: str = "", price: float = 0.0,
                initial_quantity: int = 0) -> dict:
    """
    Add a product to a store and create its inventory entry.

    Returns
    -------
    {"success": True,  "product_id": <int>}
    {"success": False, "error":      <str>}
    """
    if not name:
        return {"success": False, "error": "Product name is required."}
    if price < 0:
        return {"success": False, "error": "Price cannot be negative."}

    now = datetime.utcnow().isoformat()

    try:
        with _get_conn(STORES_DB) as conn:
            # verify store exists
            store = conn.execute(
                "SELECT id FROM stores WHERE id = ?", (store_id,)
            ).fetchone()
            if not store:
                return {"success": False, "error": "Store not found."}

            cursor = conn.execute(
                "INSERT INTO products (store_id, name, description, price, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (store_id, name.strip(), description.strip(), price, now)
            )
            product_id = cursor.lastrowid

            conn.execute(
                "INSERT INTO inventory (product_id, store_id, quantity, updated_at) "
                "VALUES (?, ?, ?, ?)",
                (product_id, store_id, initial_quantity, now)
            )
            conn.commit()
            return {"success": True, "product_id": product_id}

    except Exception as e:
        return {"success": False, "error": f"Database error: {e}"}


def list_products(store_id: int) -> dict:
    """
    Return all products with their current inventory for a given store.

    Returns
    -------
    {"success": True,  "products": [...]}
    {"success": False, "error":    <str>}
    """
    try:
        with _get_conn(STORES_DB) as conn:
            rows = conn.execute("""
                SELECT p.id, p.name, p.description, p.price,
                       COALESCE(i.quantity, 0) AS quantity
                FROM   products  p
                LEFT JOIN inventory i
                       ON i.product_id = p.id AND i.store_id = p.store_id
                WHERE  p.store_id = ?
                ORDER  BY p.name
            """, (store_id,)).fetchall()

        return {
            "success": True,
            "products": [dict(r) for r in rows]
        }
    except Exception as e:
        return {"success": False, "error": f"Database error: {e}"}


# ──────────────────────────────────────────────
# INVENTORY  –  UPDATE
# ──────────────────────────────────────────────

def update_inventory(store_id: int, product_id: int, quantity: int) -> dict:
    """
    Set the stock quantity for a product belonging to a store.

    Returns
    -------
    {"success": True}
    {"success": False, "error": <str>}
    """
    if quantity < 0:
        return {"success": False, "error": "Quantity cannot be negative."}

    now = datetime.utcnow().isoformat()

    try:
        with _get_conn(STORES_DB) as conn:
            result = conn.execute(
                "UPDATE inventory SET quantity = ?, updated_at = ? "
                "WHERE product_id = ? AND store_id = ?",
                (quantity, now, product_id, store_id)
            )
            conn.commit()

            if result.rowcount == 0:
                return {"success": False, "error": "Inventory record not found. "
                                                    "Make sure the product belongs to this store."}
            return {"success": True}

    except Exception as e:
        return {"success": False, "error": f"Database error: {e}"}
