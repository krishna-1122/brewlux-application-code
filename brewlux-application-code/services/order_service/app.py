"""BrewLux order microservice.

This service intentionally does not handle payment information. The order status
endpoint is demo-only and must be protected by authentication before public use.
"""
from __future__ import annotations

import os
import re
import uuid
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from mysql.connector import Error
from shared.db import get_connection
from shared.http import error_response

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ALLOWED_STATUSES = {"PENDING", "CONFIRMED", "PREPARING", "READY", "COMPLETED", "CANCELLED"}
TAX_RATE = Decimal(os.getenv("TAX_RATE", "0.05"))

def money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def create_app(test_config=None):
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024
    if test_config:
        app.config.update(test_config)
    CORS(app, resources={r"/api/*": {"origins": os.getenv("CORS_ORIGINS", "*")}})

    catalog_url = os.getenv("CATALOG_SERVICE_URL", "http://127.0.0.1:5001").rstrip("/")

    def fetch_products(product_ids):
        """Fetch product details from catalog service; do not trust client-sent prices."""
        try:
            response = requests.get(
                f"{catalog_url}/api/v1/products",
                params={"per_page": 48},
                timeout=(2, 5),
            )
            response.raise_for_status()
            products = response.json().get("items", [])
        except (requests.RequestException, ValueError):
            raise RuntimeError("Catalog service is unavailable")
        product_map = {int(p["id"]): p for p in products}
        missing = [pid for pid in product_ids if pid not in product_map]
        if missing:
            raise ValueError(f"Unavailable product IDs: {', '.join(map(str, missing))}")
        return product_map

    @app.get("/health")
    def health():
        try:
            conn = get_connection()
            conn.close()
            return jsonify({"status": "healthy", "service": "order-service", "database": "reachable"}), 200
        except Error:
            return jsonify({"status": "degraded", "service": "order-service", "database": "unavailable"}), 503

    @app.post("/api/v1/orders")
    def create_order():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return error_response("INVALID_JSON", "Request body must be a JSON object", 400)

        customer = payload.get("customer")
        delivery = payload.get("delivery") or {}
        items = payload.get("items")
        if not isinstance(customer, dict):
            return error_response("INVALID_CUSTOMER", "customer is required", 400)

        name = str(customer.get("name", "")).strip()
        email = str(customer.get("email", "")).strip().lower()
        phone = str(customer.get("phone", "")).strip()[:30] or None
        address = str(delivery.get("address", "")).strip()[:500] or None
        notes = str(delivery.get("notes", "")).strip()[:500] or None

        if not 2 <= len(name) <= 150:
            return error_response("INVALID_CUSTOMER_NAME", "Customer name must be 2–150 characters", 400)
        if not EMAIL_RE.match(email) or len(email) > 254:
            return error_response("INVALID_EMAIL", "A valid customer email is required", 400)
        if not isinstance(items, list) or not items or len(items) > 30:
            return error_response("INVALID_ITEMS", "Provide between 1 and 30 distinct order lines", 400)

        quantities = {}
        for item in items:
            if not isinstance(item, dict):
                return error_response("INVALID_ITEM", "Each item must be an object", 400)
            try:
                product_id = int(item.get("product_id"))
                quantity = int(item.get("quantity"))
            except (TypeError, ValueError):
                return error_response("INVALID_ITEM", "product_id and quantity must be integers", 400)
            if product_id < 1 or quantity < 1 or quantity > 20:
                return error_response("INVALID_ITEM", "Product ID must be positive and quantity must be 1–20", 400)
            quantities[product_id] = quantities.get(product_id, 0) + quantity
            if quantities[product_id] > 20:
                return error_response("INVALID_QUANTITY", "Maximum quantity per product is 20", 400)

        try:
            product_map = fetch_products(list(quantities))
        except ValueError as exc:
            return error_response("PRODUCT_UNAVAILABLE", str(exc), 400)
        except RuntimeError:
            return error_response("CATALOG_UNAVAILABLE", "Unable to validate products right now", 503)

        normalized_items = []
        subtotal = Decimal("0.00")
        for product_id, quantity in quantities.items():
            product = product_map[product_id]
            if not product.get("available") or int(product.get("stock_quantity", 0)) < quantity:
                return error_response("OUT_OF_STOCK", f"{product['name']} is not available in the requested quantity", 409)
            unit_price = money(product["price"])
            line_total = money(unit_price * quantity)
            subtotal += line_total
            normalized_items.append({
                "product_id": product_id, "product_name": product["name"],
                "quantity": quantity, "unit_price": unit_price, "line_total": line_total
            })

        subtotal = money(subtotal)
        tax_amount = money(subtotal * TAX_RATE)
        total = money(subtotal + tax_amount)
        order_number = f"BRW-{datetime.now(timezone.utc):%y%m%d}-{uuid.uuid4().hex[:8].upper()}"

        conn = cursor = None
        try:
            conn = get_connection()
            conn.start_transaction()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO orders
                    (order_number, customer_name, customer_email, customer_phone,
                     delivery_address, notes, status, subtotal, tax_amount, total_amount)
                VALUES (%s, %s, %s, %s, %s, %s, 'PENDING', %s, %s, %s)
            """, (order_number, name, email, phone, address, notes, subtotal, tax_amount, total))
            order_id = cursor.lastrowid
            cursor.executemany("""
                INSERT INTO order_items
                    (order_id, product_id, product_name, quantity, unit_price, line_total)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [
                (order_id, i["product_id"], i["product_name"], i["quantity"], i["unit_price"], i["line_total"])
                for i in normalized_items
            ])
            conn.commit()
            return jsonify({
                "message": "Order created successfully",
                "order": {
                    "order_number": order_number,
                    "status": "PENDING",
                    "items": [{
                        "product_id": i["product_id"], "product_name": i["product_name"],
                        "quantity": i["quantity"], "unit_price": float(i["unit_price"]),
                        "line_total": float(i["line_total"])
                    } for i in normalized_items],
                    "subtotal": float(subtotal),
                    "tax_amount": float(tax_amount),
                    "total_amount": float(total),
                    "currency": "INR"
                }
            }), 201
        except Error:
            if conn:
                conn.rollback()
            app.logger.exception("Order persistence failed")
            return error_response("DATABASE_UNAVAILABLE", "Could not save your order", 503)
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @app.get("/api/v1/orders/<order_number>")
    def get_order(order_number):
        email = (request.args.get("email") or "").strip().lower()
        if not email:
            return error_response("EMAIL_REQUIRED", "Provide the order email to look up this order", 400)
        conn = cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, order_number, customer_name, customer_email, status,
                       subtotal, tax_amount, total_amount, created_at
                FROM orders WHERE order_number = %s AND customer_email = %s
            """, (order_number, email))
            order = cursor.fetchone()
            if not order:
                return error_response("ORDER_NOT_FOUND", "No matching order was found", 404)
            cursor.execute("""
                SELECT product_id, product_name, quantity, unit_price, line_total
                FROM order_items WHERE order_id = %s ORDER BY id
            """, (order["id"],))
            items = cursor.fetchall()
            order["items"] = items
            order["subtotal"] = float(order["subtotal"])
            order["tax_amount"] = float(order["tax_amount"])
            order["total_amount"] = float(order["total_amount"])
            order["created_at"] = order["created_at"].isoformat()
            for item in order["items"]:
                item["unit_price"] = float(item["unit_price"])
                item["line_total"] = float(item["line_total"])
            return jsonify({"order": order, "currency": "INR"}), 200
        except Error:
            app.logger.exception("Order lookup failed")
            return error_response("DATABASE_UNAVAILABLE", "Order lookup is temporarily unavailable", 503)
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @app.get("/api/v1/orders")
    def list_customer_orders():
        email = (request.args.get("email") or "").strip().lower()
        if not EMAIL_RE.match(email):
            return error_response("INVALID_EMAIL", "Provide a valid email address", 400)
        conn = cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT order_number, status, subtotal, tax_amount, total_amount, created_at
                FROM orders WHERE customer_email = %s
                ORDER BY created_at DESC LIMIT 50
            """, (email,))
            rows = cursor.fetchall()
            for row in rows:
                row["subtotal"] = float(row["subtotal"])
                row["tax_amount"] = float(row["tax_amount"])
                row["total_amount"] = float(row["total_amount"])
                row["created_at"] = row["created_at"].isoformat()
            return jsonify({"items": rows}), 200
        except Error:
            app.logger.exception("Customer order listing failed")
            return error_response("DATABASE_UNAVAILABLE", "Order history is temporarily unavailable", 503)
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @app.patch("/api/v1/orders/<order_number>/status")
    def update_order_status(order_number):
        # Demo-only endpoint. Add authentication, authorization and audit logging before public deployment.
        payload = request.get_json(silent=True) or {}
        status = str(payload.get("status", "")).upper()
        if status not in ALLOWED_STATUSES:
            return error_response("INVALID_STATUS", f"status must be one of: {', '.join(sorted(ALLOWED_STATUSES))}", 400)
        conn = cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE orders SET status = %s WHERE order_number = %s", (status, order_number))
            if cursor.rowcount == 0:
                conn.rollback()
                return error_response("ORDER_NOT_FOUND", "Order not found", 404)
            conn.commit()
            return jsonify({"order_number": order_number, "status": status}), 200
        except Error:
            if conn:
                conn.rollback()
            app.logger.exception("Order status update failed")
            return error_response("DATABASE_UNAVAILABLE", "Could not update order status", 503)
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @app.errorhandler(404)
    def not_found(_):
        return error_response("NOT_FOUND", "The requested order resource was not found", 404)

    @app.errorhandler(413)
    def too_large(_):
        return error_response("REQUEST_TOO_LARGE", "Request body is too large", 413)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5002")), debug=False)
