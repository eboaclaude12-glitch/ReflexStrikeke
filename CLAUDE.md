# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ReflexStrike** is a static-site French-language e-commerce frontend for boxing equipment (speed bags, professional training gear). There is no build step — the site is ready to serve as-is.

A secondary file (`valentine.html`) is a standalone personal page unrelated to the store.

## Running the Site

Open `index.html` directly in a browser, or serve the repo root with any static file server:

```bash
# Python
python3 -m http.server 8000

# Node (npx)
npx serve .
```

No dependencies to install, no compilation required.

## Architecture

Everything lives in `index.html` — no external JS files or CSS files are referenced except Google Fonts and no build tooling.

**JavaScript structure (all inline in `index.html`):**

- `products[]` — hard-coded array of 6 product objects (`id`, `name`, `price`, `description`, `features[]`, `badge`). Rendered into the Products section on page load.
- Cart state lives in a plain `cart` object (`{ [productId]: quantity }`).
- Cart functions: `addToCart(id)`, `updateCart()`, `updateQuantity(id, delta)`, `removeFromCart(id)`, `checkout()` (mock alert).
- `renderProducts()` builds product cards dynamically from the array.
- Toast notifications (`showToast(msg)`) are CSS-animated divs created/removed in JS.

**CSS:** all inline `<style>` in `index.html`.

- Design tokens: primary `#ff6b35` (orange), secondary `#1a1a1a`, accent `#ffd93d`.
- Fonts: `Oswald` (headings) and `Outfit` (body) via Google Fonts.
- Responsive breakpoints: 1024 px and 768 px.

**`valentine.html`** is fully self-contained with its own inline CSS/JS. The "No" button evades the cursor via `mouseover`; clicking "Yes" triggers a heart-burst animation. No shared code with `index.html`.

## Planned MT5 Project

This repo is also the target for a **Smart-Money Toolkit for MetaTrader 5** (see project brief). When that work begins, the layout will be:

```
/Indicators/LiquiditySweeps_iFVG.mq5
/Experts/SmartMoneyEA.mq5          # only if scope B/C selected
/Include/SmartMoney/               # shared structs/helpers
/README.md
/CHANGELOG.md
```

The `.mq5` source file (v1.10) must be uploaded to the repo before work can start.
