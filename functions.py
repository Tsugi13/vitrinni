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
# Funções QoL (Quality of Life)
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
    conn.row_factory = sqlite3.Row          # Acesso de colunas por nome
    conn.execute("PRAGMA journal_mode=WAL") # Escritas concorrentes sem travar leitura
    return conn


# Inicialização dos BDs

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


# Cadastro e Login de Usuários

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


# Popular BDs com lojas e produtos iniciais para teste.

def seed_stores():
    now = datetime.utcnow().isoformat()

    stores = [
        {
            "store_name": "Kimono King",
            "owner_name": "Rafael Mendes",
            "phone": "11 91234-5678",
            "email": "contato@kimonoking.com.br",
            "password": _hash_password("kimono123"),
            "products": [
                ("Kimono Adulto A2 – Branco",  "Tecido 100% algodão pré-encolhido. Aprovado IBJJF.",        249.90, 30),
                ("Kimono Infantil M1 – Azul",  "Leve e durável para crianças de 6-10 anos.",                189.90, 20),
                ("Faixa Branca Bordada",        "Algodão resistente, 2,5 m, ideal para iniciantes.",          39.90, 50),
                ("Faixa Preta Bordada",         "Acabamento premium, bordado personalizado disponível.",       89.90, 15),
                ("Rashguard Manga Longa",        "Compressão suave, proteção contra abrasão no tatame.",       119.90, 25),
                ("Protetor Bucal Duplo",         "Silicone atóxico moldável, proteção para dentes e gengivas.", 29.90, 60),
            ]
        },
        {
            "store_name": "Muay Store",
            "owner_name": "Wanderlei Costa",
            "phone": "21 98765-4321",
            "email": "muaystore@luta.com.br",
            "password": _hash_password("muay123"),
            "products": [
                ("Luva de Boxe Pro 12oz",       "Couro sintético premium, espuma de alta densidade.",        149.90, 40),
                ("Luva de Boxe Pro 16oz",       "Ideal para sparring pesado e treinos com parceiro.",        179.90, 25),
                ("Capacete Muay Thai",          "Cobertura total de orelhas, ventilação aprimorada.",        209.90, 18),
                ("Caneleira Gel Pro",            "Proteção de gel absorvente, fechamento em velcro.",         189.90, 22),
                ("Bandagem Elástica 5m",         "Proteção extra para punhos e articulações, par incluso.",    34.90, 80),
                ("Shorts Muay Thai Tiger",       "Tecido acetinado, elástico na cintura, corte tailandês.",    99.90, 35),
                ("Saco de Pancada 40kg",         "Couro ecológico, recheio de areia e espuma.",               499.90,  8),
            ]
        },
        {
            "store_name": "Tatame Total",
            "owner_name": "Fernanda Yamamoto",
            "phone": "31 97654-3210",
            "email": "contato@tatametotal.com.br",
            "password": _hash_password("tatame123"),
            "products": [
                ("Tatame EVA 1m x 1m – 20mm",  "Alta densidade, encaixe perfeito, superfície antiderrapante.", 59.90, 100),
                ("Tatame EVA 1m x 1m – 40mm",  "Versão premium para quedas e arremessos pesados.",             89.90,  60),
                ("Cronômetro Digital Tatame",   "Display LED, modos luta/descanso, buzzer integrado.",          99.90,  12),
                ("Manequim de Treino 1,70m",    "Borracha sólida, base estabilizadora, 43 kg.",               799.90,   5),
                ("Kit Defesa Pessoal – Bastões","Par de bastões de polipropileno, cabo emborrachado.",           49.90,  30),
                ("Espelho Treinamento 2x1m",    "Vidro temperado com moldura de alumínio.",                   299.90,   7),
            ]
        },
        {
            "store_name": "Dragon Fight Shop",
            "owner_name": "Carlos Dragão",
            "phone": "41 96543-2109",
            "email": "dragon@fightshop.com.br",
            "password": _hash_password("dragon123"),
            "products": [
                ("Uniforme Taekwondo Dobok",     "Tecido leve sanfonado, ideal para chutes altos.",            159.90, 28),
                ("Protetor de Canela TKD",       "Espuma moldada, cobertura de tornozelo, adulto.",             69.90, 40),
                ("Protetor de Antebraço",         "Par, espuma EVA 15mm, fechamento ajustável.",                54.90, 35),
                ("Colete de Pontuação Eletrônico","Homologado WT, sensor de impacto integrado.",               599.90,  6),
                ("Faixa Poomsae – Todas as cores","Poliéster resistente, costura dupla, 2,8m.",                29.90, 70),
                ("Luva Sparring Taekwondo",       "Proteção mão inteira, velcro de ajuste, par.",               79.90, 20),
            ]
        },
        {
            "store_name": "Judô & Cia",
            "owner_name": "Mariana Nakamura",
            "phone": "51 95432-1098",
            "email": "judoecia@dojo.com.br",
            "password": _hash_password("judo123"),
            "products": [
                ("Judogi Adulto 750g/m²",       "Algodão reforçado, homologado IJF, branco.",                 329.90, 20),
                ("Judogi Infantil 450g/m²",     "Leve e flexível para crianças, azul ou branco.",             199.90, 18),
                ("Faixa Judô – todas as cores", "Algodão torcido, 2,6m, resistente a lavagens.",               35.90, 60),
                ("Joelheira Neoprene",           "Compressão uniforme, abertura patelar, par.",                 59.90, 45),
                ("Luva de Proteção Kata",        "Espuma 10mm, sem dedos, par.",                               44.90, 30),
                ("Bolsa de Judô GI Bag",         "Compartimentos separados para kimono molhado/seco.",          89.90, 14),
            ]
        },
    ]

    with _get_conn(STORES_DB) as conn:
        existing = conn.execute("SELECT COUNT(*) FROM stores").fetchone()[0]
        if existing > 0:
            return  # already seeded

        for s in stores:
            cur = conn.execute(
                "INSERT INTO stores (store_name, owner_name, phone, email, password, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (s["store_name"], s["owner_name"], s["phone"],
                 s["email"], s["password"], now)
            )
            store_id = cur.lastrowid

            for (pname, pdesc, pprice, pqty) in s["products"]:
                pcur = conn.execute(
                    "INSERT INTO products (store_id, name, description, price, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (store_id, pname, pdesc, pprice, now)
                )
                product_id = pcur.lastrowid
                conn.execute(
                    "INSERT INTO inventory (product_id, store_id, quantity, updated_at) "
                    "VALUES (?, ?, ?, ?)",
                    (product_id, store_id, pqty, now)
                )

        conn.commit()
        print(f"[seed] {len(stores)} stores and their products inserted.")


# Pesquisar lojas por nome

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