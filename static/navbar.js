/**
 * navbar.js — shared across every Vitrinni page
 * Handles: menu dropdown, cart dropdown, cart badge, add-to-cart
 */

(function () {

    // ── icon map ──
    const iconMap = [
        [/luva|boxe|sparring/i,            'fas fa-mitten'],
        [/kimono|judogi|dobok|uniforme/i,  'fas fa-tshirt'],
        [/faixa/i,                         'fas fa-ribbon'],
        [/caneleira/i,                     'fas fa-shoe-prints'],
        [/capacete/i,                      'fas fa-hard-hat'],
        [/bandagem/i,                      'fas fa-band-aid'],
        [/rashguard|shorts/i,              'fas fa-running'],
        [/tatame|tapete/i,                 'fas fa-border-all'],
        [/saco.*pancada/i,                 'fas fa-circle'],
        [/cronômetro|timer/i,              'fas fa-stopwatch'],
        [/manequim/i,                      'fas fa-male'],
        [/bastão/i,                        'fas fa-baseball-bat-ball'],
        [/protetor.*bucal/i,               'fas fa-tooth'],
        [/protetor|joelheira/i,            'fas fa-shield-alt'],
        [/bolsa|bag/i,                     'fas fa-shopping-bag'],
    ];
    function getIcon(name) {
        for (const [re, icon] of iconMap) if (re.test(name)) return icon;
        return 'fas fa-fist-raised';
    }

    function fmt(val) {
        return val.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    }

    // ── cart storage ──
    function getCart() {
        return JSON.parse(sessionStorage.getItem('vitrinni_cart') || '[]');
    }
    function saveCart(cart) {
        sessionStorage.setItem('vitrinni_cart', JSON.stringify(cart));
    }

    // ── add to cart (called by product buttons) ──
    window.addToCart = function (id, name, store_name, price, btn) {
        id = Number(id);
        price = Number(price);
        const cart = getCart();
        const existing = cart.find(i => i.id === id);
        if (existing) existing.qty++;
        else cart.push({ id, name, store_name, price, qty: 1 });
        saveCart(cart);
        renderCartDropdown();

        // button feedback
        if (btn) {
            const orig = btn.textContent;
            btn.textContent = '✓ Adicionado';
            btn.style.background = '#2e7d32';
            btn.disabled = true;
            setTimeout(() => {
                btn.textContent = orig;
                btn.style.background = '';
                btn.disabled = false;
            }, 1000);
        }

        // briefly open cart dropdown
        const dd = document.getElementById('cartDropdown');
        if (dd) {
            dd.classList.add('open');
            setTimeout(() => dd.classList.remove('open'), 2200);
        }
    };

    // ── render cart dropdown contents ──
    function renderCartDropdown() {
        const cart = getCart();
        const badge    = document.getElementById('cartCountBadge');
        const itemsEl  = document.getElementById('cartDropdownItems');
        const footerEl = document.getElementById('cartDropdownFooter');
        const totalEl  = document.getElementById('cartDropdownTotal');

        if (!badge) return; // navbar not present on this page

        const totalQty = cart.reduce((s, i) => s + i.qty, 0);
        badge.textContent = totalQty;
        badge.style.display = totalQty > 0 ? 'inline' : 'none';

        if (!cart.length) {
            itemsEl.innerHTML = `<div class="cart-dropdown-empty">
                <i class="fas fa-cart-arrow-down"></i><p>Carrinho vazio</p>
            </div>`;
            footerEl.style.display = 'none';
            return;
        }

        const total = cart.reduce((s, i) => s + i.price * i.qty, 0);
        itemsEl.innerHTML = cart.map(i => `
            <div class="cart-drop-item">
                <div class="cart-drop-icon"><i class="${getIcon(i.name)}"></i></div>
                <div class="cart-drop-info">
                    <div class="cart-drop-name">${i.name}</div>
                    <div class="cart-drop-qty">x${i.qty} · ${i.store_name}</div>
                </div>
                <div class="cart-drop-price">${fmt(i.price * i.qty)}</div>
            </div>`).join('');

        totalEl.textContent = fmt(total);
        footerEl.style.display = 'block';
    }

    // ── toggle dropdowns ──
    window.toggleMenuDropdown = function () {
        const menu = document.getElementById('menuDropdown');
        const cart = document.getElementById('cartDropdown');
        if (!menu) return;
        cart && cart.classList.remove('open');
        menu.classList.toggle('open');
    };

    window.toggleCartDropdown = function () {
        const cart = document.getElementById('cartDropdown');
        const menu = document.getElementById('menuDropdown');
        if (!cart) return;
        menu && menu.classList.remove('open');
        cart.classList.toggle('open');
        if (cart.classList.contains('open')) renderCartDropdown();
    };

    // close on outside click
    document.addEventListener('click', function (e) {
        const cartWrap = document.getElementById('carrinhoWrapper');
        const menuWrap = document.getElementById('menuWrapper');
        if (cartWrap && !cartWrap.contains(e.target))
            document.getElementById('cartDropdown')?.classList.remove('open');
        if (menuWrap && !menuWrap.contains(e.target))
            document.getElementById('menuDropdown')?.classList.remove('open');
    });

    // expose for other pages (e.g. loja.html) to trigger a re-render
    window._navbarRenderCart = renderCartDropdown;

    // init badge on every page load
    renderCartDropdown();

})();
