/* BrewLux storefront. The reverse proxy will route these same-origin API paths. */
(() => {
  "use strict";

  const API = {
    catalog: window.BREWLUX_CATALOG_URL || "/api/catalog",
    orders: window.BREWLUX_ORDERS_URL || "/api/orders"
  };

  const state = { products: [], category: "", search: "", cart: loadCart() };
  const $ = (selector) => document.querySelector(selector);
  const productGrid = $("#product-grid");
  const toast = $("#toast");

  function loadCart() {
    try { return JSON.parse(localStorage.getItem("brewlux-cart") || "[]"); }
    catch { return []; }
  }

  function saveCart() {
    localStorage.setItem("brewlux-cart", JSON.stringify(state.cart));
    renderCartCount();
  }

  function safeText(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[char]);
  }

  function money(value) {
    return new Intl.NumberFormat("en-IN", {
      style: "currency", currency: "INR", maximumFractionDigits: 2
    }).format(Number(value) || 0);
  }

  function notify(message) {
    toast.textContent = message;
    toast.classList.add("show");
    window.setTimeout(() => toast.classList.remove("show"), 2400);
  }

  async function apiGet(url) {
    const response = await fetch(url, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`Request failed (${response.status})`);
    return response.json();
  }

  async function loadProducts() {
    productGrid.innerHTML = '<div class="loading-state">Preparing your coffee menu…</div>';
    const params = new URLSearchParams({ per_page: "48", sort: "featured" });
    if (state.category) params.set("category", state.category);
    if (state.search) params.set("search", state.search);
    try {
      const data = await apiGet(`${API.catalog}/v1/products?${params}`);
      state.products = data.items || [];
      renderProducts(state.products);
      $("#api-note").textContent = `${data.pagination?.total ?? state.products.length} carefully selected favourites.`;
    } catch (error) {
      productGrid.innerHTML = '<div class="empty-state"><strong>Your coffee menu is taking a moment.</strong><br>Start the catalog API and try refreshing this page.</div>';
      $("#api-note").textContent = "Catalog API is not reachable yet. The frontend will work once we add the proxy and start the services.";
    }
  }

  function renderProducts(products) {
    if (!products.length) {
      productGrid.innerHTML = '<div class="empty-state">No coffees match that search. Try another flavour.</div>';
      return;
    }
    productGrid.innerHTML = products.map((p) => `
      <article class="product-card">
        <div class="product-photo">
          <img src="${safeText(p.image_url)}" alt="${safeText(p.name)}" loading="lazy"
               onerror="this.src='https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?auto=format&fit=crop&w=900&q=80'">
          ${p.featured ? '<span class="product-badge">BrewLux favourite</span>' : `<span class="product-badge">${safeText(p.roast_level || "CRAFTED")}</span>`}
          <button class="add-button" data-add="${Number(p.id)}" aria-label="Add ${safeText(p.name)} to bag">+</button>
        </div>
        <div class="product-meta"><h3>${safeText(p.name)}</h3><span class="product-price">${money(p.price)}</span></div>
        <p class="product-origin">${safeText(p.origin || p.category?.name || "BrewLux selection")}</p>
        <p class="product-description">${safeText(p.description || "")}</p>
      </article>`).join("");
  }

  function addToCart(productId) {
    const product = state.products.find((item) => Number(item.id) === Number(productId));
    if (!product) return notify("Please refresh the menu and try again.");
    const existing = state.cart.find((item) => Number(item.id) === Number(productId));
    if (existing) {
      if (existing.quantity >= 20) return notify("Maximum quantity reached.");
      existing.quantity += 1;
    } else {
      state.cart.push({
        id: Number(product.id), name: product.name, price: Number(product.price),
        image_url: product.image_url, quantity: 1
      });
    }
    saveCart();
    renderCart();
    notify(`${product.name} added to your bag`);
  }

  function renderCartCount() {
    const count = state.cart.reduce((sum, item) => sum + item.quantity, 0);
    $("#cart-count").textContent = count;
    $("#drawer-count").textContent = `(${count})`;
  }

  function renderCart() {
    const host = $("#cart-items");
    if (!state.cart.length) {
      host.innerHTML = '<p class="empty-cart">Your bag is waiting for something lovely.</p>';
      $("#cart-total").textContent = money(0);
      return;
    }
    host.innerHTML = state.cart.map((item) => `
      <article class="cart-row">
        <img src="${safeText(item.image_url)}" alt="" loading="lazy">
        <div><h3>${safeText(item.name)}</h3><p>${money(item.price)} each</p>
          <div class="qty-controls">
            <button data-qty="-1" data-id="${item.id}" aria-label="Decrease quantity">−</button>
            <span>${item.quantity}</span>
            <button data-qty="1" data-id="${item.id}" aria-label="Increase quantity">+</button>
          </div>
        </div>
        <span class="line-price">${money(item.price * item.quantity)}</span>
      </article>`).join("");
    const total = state.cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
    $("#cart-total").textContent = money(total);
  }

  function changeQuantity(id, delta) {
    const item = state.cart.find((entry) => Number(entry.id) === Number(id));
    if (!item) return;
    item.quantity += delta;
    if (item.quantity <= 0) state.cart = state.cart.filter((entry) => Number(entry.id) !== Number(id));
    if (item.quantity > 20) item.quantity = 20;
    saveCart();
    renderCart();
  }

  function openCart() {
    $("#cart-drawer").classList.add("open");
    $("#cart-drawer").setAttribute("aria-hidden", "false");
    $("#overlay").classList.add("show");
    document.body.style.overflow = "hidden";
  }

  function closeCart() {
    $("#cart-drawer").classList.remove("open");
    $("#cart-drawer").setAttribute("aria-hidden", "true");
    $("#overlay").classList.remove("show");
    document.body.style.overflow = "";
  }

  async function checkout() {
    const message = $("#checkout-message");
    message.textContent = "";
    if (!state.cart.length) {
      message.textContent = "Add a coffee to your bag first.";
      return;
    }
    const name = window.prompt("Your name for the order:");
    if (!name) return;
    const email = window.prompt("Your email for order lookup:");
    if (!email) return;
    const address = window.prompt("Delivery address (demo field):") || "";
    const payload = {
      customer: { name: name.trim(), email: email.trim() },
      delivery: { address },
      items: state.cart.map((item) => ({ product_id: item.id, quantity: item.quantity }))
    };
    try {
      const response = await fetch(`${API.orders}/v1/orders`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error?.message || "Could not create the order");
      state.cart = [];
      saveCart();
      renderCart();
      message.textContent = `Order ${data.order.order_number} placed. Total ${money(data.order.total_amount)}.`;
      notify("Your BrewLux order is in!");
    } catch (error) {
      message.textContent = `${error.message}. Ensure the order and catalog APIs are running.`;
    }
  }

  $("#category-tabs").addEventListener("click", (event) => {
    const button = event.target.closest("[data-category]");
    if (!button) return;
    state.category = button.dataset.category;
    document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("active", tab === button));
    loadProducts();
  });

  let searchTimer;
  $("#search-input").addEventListener("input", (event) => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(() => {
      state.search = event.target.value.trim();
      loadProducts();
    }, 250);
  });

  productGrid.addEventListener("click", (event) => {
    const button = event.target.closest("[data-add]");
    if (button) addToCart(button.dataset.add);
  });
  $("#cart-items").addEventListener("click", (event) => {
    const button = event.target.closest("[data-qty]");
    if (button) changeQuantity(button.dataset.id, Number(button.dataset.qty));
  });
  $("#cart-toggle").addEventListener("click", openCart);
  $("#cart-close").addEventListener("click", closeCart);
  $("#overlay").addEventListener("click", closeCart);
  $("#checkout-button").addEventListener("click", checkout);
  $("#newsletter-form").addEventListener("submit", (event) => {
    event.preventDefault();
    $("#newsletter-message").textContent = "Thanks — newsletter signup is a visual demo for now.";
    event.target.reset();
  });
  $("#year").textContent = new Date().getFullYear();
  renderCartCount();
  renderCart();
  loadProducts();
})();
