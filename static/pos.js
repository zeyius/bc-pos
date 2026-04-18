let cart = {};

function addToCart(id, name, price) {
    if (!cart[id]) {
        cart[id] = { name: name, price: price, qty: 0 };
    }
    cart[id].qty += 1;
    renderCart();
}

function renderCart() {
    const cartContainer = document.getElementById("cart-items");
    cartContainer.innerHTML = "";

    let subtotal = 0;

    for (let id in cart) {
        let item = cart[id];
        let lineTotal = item.price * item.qty;
        subtotal += lineTotal;

        cartContainer.innerHTML += `
            <div class="cart-item">
                <div>
                    <strong>${item.name}</strong><br>
                    ${item.price} DA x ${item.qty}
                </div>
                <div class="cart-controls">
                    <button onclick="decreaseItem(${id})">-</button>
                    <button onclick="increaseItem(${id})">+</button>
                </div>
            </div>
        `;
    }

    document.getElementById("subtotal").innerText = subtotal;
    calculateChange();
}

function increaseItem(id) {
    cart[id].qty += 1;
    renderCart();
}

function decreaseItem(id) {
    cart[id].qty -= 1;
    if (cart[id].qty <= 0) {
        delete cart[id];
    }
    renderCart();
}

function calculateChange() {
    let subtotal = parseFloat(document.getElementById("subtotal").innerText) || 0;
    let cash = parseFloat(document.getElementById("cash").value) || 0;
    let change = cash - subtotal;

    document.getElementById("change").innerText = change >= 0 ? change : 0;
}

function submitSale() {
    if (Object.keys(cart).length === 0) {
        return;
    }

    let subtotal = parseFloat(document.getElementById("subtotal").innerText) || 0;
    let cash = parseFloat(document.getElementById("cash").value);

    if (isNaN(cash)) {
        alert("Enter cash given");
        return;
    }

    if (cash < subtotal) {
        alert("Cash is not enough");
        return;
    }

    fetch("/process_sale", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(cart)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            cart = {};
            renderCart();
            document.getElementById("cash").value = "";
            document.getElementById("change").innerText = "0";
        }
    });
}

function toggleCategory(id) {
  const section = document.getElementById("cat_" + id);
  if (!section) return;

  const isCollapsed = section.classList.contains("is-collapsed");

  if (isCollapsed) {
    // OPEN smoothly
    section.classList.remove("is-collapsed");

    // set a real height to animate to
    section.style.maxHeight = section.scrollHeight + "px";

    // after animation, let it grow naturally if content changes
    const onEnd = (e) => {
      if (e.propertyName !== "max-height") return;
      section.style.maxHeight = "none";
      section.removeEventListener("transitionend", onEnd);
    };
    section.addEventListener("transitionend", onEnd);

  } else {
    // CLOSE smoothly
    // if maxHeight was "none", set it to current height first
    section.style.maxHeight = section.scrollHeight + "px";

    requestAnimationFrame(() => {
      section.classList.add("is-collapsed");
      section.style.maxHeight = "0px";
    });
  }
}

document.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
        e.preventDefault();
        submitSale();
    }
});

