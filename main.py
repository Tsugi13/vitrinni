"""
main.py
-------
Interactive terminal for manually testing every backend function.
Run with: python main.py
"""

import os
import sys
from functions import (
    init_users_db, init_stores_db,
    user_signup,  user_login,
    store_signup, store_login,
    search_stores,
    add_product,  list_products, update_inventory,
)

init_users_db()
init_stores_db()


# ──────────────────────────────────────────────
# 
# ──────────────────────────────────────────────

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def hr():
    print("─" * 44)

def show_result(result: dict):
    hr()
    if result.get("success"):
        print("  ✓  SUCCESSO")
        for k, v in result.items():
            if k != "success":
                print(f"     {k}: {v}")
    else:
        print("  ✗  ERRO")
        print(f"     error: {result.get('error')}")
    hr()
    input("  Aperte Enter para continuar...")

def prompt(label: str, required: bool = True) -> str:
    while True:
        val = input(f"  {label}: ").strip()
        if val or not required:
            return val
        print("  (esse campo é obrigatório)")

def prompt_float(label: str, default: float = 0.0) -> float:
    while True:
        raw = input(f"  {label} [{default}]: ").strip()
        if not raw:
            return default
        try:
            return float(raw)
        except ValueError:
            print("  Por favor, insira um número válido (use ponto para decimais).")

def prompt_int(label: str, default: int = 0) -> int:
    while True:
        raw = input(f"  {label} [{default}]: ").strip()
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError:
            print("  Por favor, insira um número inteiro válido.")


# ──────────────────────────────────────────────
# STORE PICKER  (search → confirm)
# ──────────────────────────────────────────────

def pick_store() -> dict | None:
    while True:
        term = prompt("Pesquise por nome da loja ou do dono (0 para cancelar)")
        if term == "0":
            return None

        result = search_stores(term)

        if not result["success"]:
            print(f"\n  Erro: {result['error']}\n")
            continue

        stores = result["stores"]

        if not stores:
            print(f"\n  Nenhuma loja encontrada que combine com '{term}'. Tente novamente.\n")
            continue

        # show matches
        print()
        hr()
        for i, s in enumerate(stores, 1):
            print(f"  {i}. {s['store_name']}  (owner: {s['owner_name']}, id: {s['id']})")
        hr()
        print("  0. Procure de novo")
        print()

        choice = input("  Confirme a loja (número): ").strip()

        if choice == "0":
            continue

        if choice.isdigit() and 1 <= int(choice) <= len(stores):
            chosen = stores[int(choice) - 1]
            print(f"\n  ✓ Selecionado: {chosen['store_name']}\n")
            return chosen

        print("\n  Escolha inválida, tente novamente.\n")


# ──────────────────────────────────────────────
# INDIVIDUAL FUNCTION SCREENS
# ──────────────────────────────────────────────

def screen_user_signup():
    clear()
    print("\n  ── USER SIGN-UP ──\n")
    name     = prompt("Nome")
    email    = prompt("E-mail")
    phone    = prompt("Telefone")
    password = prompt("Senha")
    show_result(user_signup(name, email, phone, password))

def screen_user_login():
    clear()
    print("\n  ── USER LOGIN ──\n")
    email    = prompt("E-mail")
    password = prompt("Senha")
    show_result(user_login(email, password))

def screen_store_signup():
    clear()
    print("\n  ── STORE SIGN-UP ──\n")
    store_name = prompt("Nome da loja")
    owner_name = prompt("Nome do dono")
    phone      = prompt("Telefone")
    email      = prompt("E-mail")
    password   = prompt("Senha")
    show_result(store_signup(store_name, owner_name, phone, email, password))

def screen_store_login():
    clear()
    print("\n  ── STORE LOGIN ──\n")
    email    = prompt("E-mail")
    password = prompt("Senha")
    show_result(store_login(email, password))

def screen_add_product():
    clear()
    print("\n  ── ADICIONAR PRODUTO ──\n")

    store = pick_store()
    if not store:
        return

    name  = prompt("Nome do produto")
    desc  = prompt("Descrição (opcional)", required=False)
    price = prompt_float("Preço")
    qty   = prompt_int("Quantidade inicial em estoque")
    show_result(add_product(store["id"], name, desc, price, qty))

def screen_list_products():
    clear()
    print("\n  ── LISTA DE PRODUTOS ──\n")

    store = pick_store()
    if not store:
        return

    result = list_products(store["id"])
    hr()
    if result["success"]:
        products = result["products"]
        if not products:
            print(f"  (nenhum produto encontrado '{store['store_name']}')")
        else:
            print(f"  Loja: {store['store_name']}\n")
            print(f"  {'ID':<5} {'Name':<20} {'Price':>8}  {'Stock':>6}")
            hr()
            for p in products:
                print(f"  {p['id']:<5} {p['name']:<20} R${p['price']:>7.2f}  {p['quantity']:>6}")
    else:
        print(f"  ✗  {result['error']}")
    hr()
    input("  Aperte Enter para continuar...")

def screen_update_inventory():
    clear()
    print("\n  ── ATUALIZAR INVENTÁRIO ──\n")

    store = pick_store()
    if not store:
        return

    listing = list_products(store["id"])
    if listing["success"] and listing["products"]:
        print(f"\n  Produtos em '{store['store_name']}':\n")
        print(f"  {'ID':<5} {'Name':<20} {'Stock':>6}")
        hr()
        for p in listing["products"]:
            print(f"  {p['id']:<5} {p['name']:<20} {p['quantity']:>6}")
        print()

    product_id = prompt_int("ID do produto a ser atualizado")
    quantity   = prompt_int("Nova quantidade")
    show_result(update_inventory(store["id"], product_id, quantity))


# ──────────────────────────────────────────────
# MAIN MENU
# ──────────────────────────────────────────────

MENU = [
    ("User sign-up",     screen_user_signup),
    ("User login",       screen_user_login),
    ("Store sign-up",    screen_store_signup),
    ("Store login",      screen_store_login),
    ("Add product",      screen_add_product),
    ("List products",    screen_list_products),
    ("Update inventory", screen_update_inventory),
]

def main():
    while True:
        clear()
        print("\n  ╔══════════════════════════════════════════╗")
        print("  ║      MARKETPLACE BACKEND — TEST MENU     ║")
        print("  ╚══════════════════════════════════════════╝\n")

        for i, (label, _) in enumerate(MENU, 1):
            print(f"    {i}. {label}")

        print("\n    0. Exit")
        print()

        choice = input("  Choose an option: ").strip()

        if choice == "0":
            print("\n  Bye!\n")
            sys.exit(0)

        if choice.isdigit() and 1 <= int(choice) <= len(MENU):
            MENU[int(choice) - 1][1]()
        else:
            input("  Invalid option. Press Enter to try again...")


if __name__ == "__main__":
    main()
