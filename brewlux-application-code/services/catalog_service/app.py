"""BrewLux catalog microservice."""
from __future__ import annotations

import os
from decimal import Decimal
from flask import Flask, jsonify, request
from flask_cors import CORS
from mysql.connector import Error
from shared.db import get_connection
from shared.http import error_response

def create_app(test_config=None):
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024
    if test_config:
        app.config.update(test_config)
    CORS(app, resources={r"/api/*": {"origins": os.getenv("CORS_ORIGINS", "*")}})

    def serialize_product(row):
        return {
            "id": row["id"],
            "sku": row["sku"],
            "name": row["name"],
            "slug": row["slug"],
            "description": row.get("description") or "",
            "origin": row.get("origin") or "House blend",
            "roast_level": row.get("roast_level") or "MEDIUM",
            "price": float(row["price"]),
            "image_url": row.get("image_url") or "",
            "available": bool(row["available"]),
            "stock_quantity": int(row["stock_quantity"]),
            "category": {
                "id": row.get("category_id"),
                "name": row.get("category_name") or "Coffee",
                "slug": row.get("category_slug") or "coffee",
            },
        }

    @app.get("/health")
    def health():
        try:
            conn = get_connection()
            conn.close()
            return jsonify({"status": "healthy", "service": "catalog-service", "database": "reachable"}), 200
        except Error:
            return jsonify({"status": "degraded", "service": "catalog-service", "database": "unavailable"}), 503

    @app.get("/api/v1/categories")
    def categories():
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT c.id, c.name, c.slug, c.description,
                       COUNT(p.id) AS product_count
                FROM categories c
                LEFT JOIN products p ON p.category_id = c.id AND p.available = TRUE
                GROUP BY c.id, c.name, c.slug, c.description
                ORDER BY c.name
            """)
            return jsonify({"items": cursor.fetchall()}), 200
        except Error:
            app.logger.exception("Could not retrieve categories")
            return error_response("DATABASE_UNAVAILABLE", "Categories are temporarily unavailable", 503)
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @app.get("/api/v1/products/featured")
    def featured_products():
        return list_products(featured_only=True)

    @app.get("/api/v1/products")
    def list_products(featured_only=False):
        try:
            page = max(1, int(request.args.get("page", "1")))
            per_page = min(48, max(1, int(request.args.get("per_page", "12"))))
        except ValueError:
            return error_response("INVALID_PAGINATION", "page and per_page must be integers", 400)

        search = (request.args.get("search") or "").strip()[:100]
        category = (request.args.get("category") or "").strip()[:90]
        sort = request.args.get("sort", "featured")
        sort_columns = {
            "featured": "p.featured DESC, p.name ASC",
            "price_asc": "p.price ASC, p.name ASC",
            "price_desc": "p.price DESC, p.name ASC",
            "name_asc": "p.name ASC",
            "newest": "p.created_at DESC",
        }
        if sort not in sort_columns:
            return error_response("INVALID_SORT", "Unsupported sort option", 400)

        where = ["p.available = TRUE"]
        params = []
        if search:
            where.append("(p.name LIKE %s OR p.description LIKE %s OR p.origin LIKE %s)")
            term = f"%{search}%"
            params.extend([term, term, term])
        if category:
            where.append("c.slug = %s")
            params.append(category)
        if featured_only:
            where.append("p.featured = TRUE")

        where_sql = " AND ".join(where)
        conn = cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(f"""
                SELECT p.id, p.sku, p.name, p.slug, p.description, p.origin,
                       p.roast_level, p.price, p.image_url, p.available,
                       p.stock_quantity, p.category_id, c.name AS category_name,
                       c.slug AS category_slug
                FROM products p
                LEFT JOIN categories c ON c.id = p.category_id
                WHERE {where_sql}
                ORDER BY {sort_columns[sort]}
                LIMIT %s OFFSET %s
            """, params + [per_page, (page - 1) * per_page])
            items = [serialize_product(row) for row in cursor.fetchall()]
            cursor.execute(f"""
                SELECT COUNT(*) AS total
                FROM products p
                LEFT JOIN categories c ON c.id = p.category_id
                WHERE {where_sql}
            """, params)
            total = cursor.fetchone()["total"]
            return jsonify({
                "items": items,
                "pagination": {
                    "page": page, "per_page": per_page, "total": total,
                    "pages": (total + per_page - 1) // per_page
                }
            }), 200
        except Error:
            app.logger.exception("Could not retrieve products")
            return error_response("DATABASE_UNAVAILABLE", "Products are temporarily unavailable", 503)
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @app.get("/api/v1/products/<int:product_id>")
    def get_product(product_id):
        conn = cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT p.id, p.sku, p.name, p.slug, p.description, p.origin,
                       p.roast_level, p.price, p.image_url, p.available,
                       p.stock_quantity, p.category_id, c.name AS category_name,
                       c.slug AS category_slug
                FROM products p LEFT JOIN categories c ON c.id = p.category_id
                WHERE p.id = %s
            """, (product_id,))
            row = cursor.fetchone()
            if not row:
                return error_response("PRODUCT_NOT_FOUND", "No product exists with this ID", 404)
            return jsonify({"item": serialize_product(row)}), 200
        except Error:
            app.logger.exception("Could not retrieve product")
            return error_response("DATABASE_UNAVAILABLE", "Product is temporarily unavailable", 503)
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @app.errorhandler(404)
    def not_found(_):
        return error_response("NOT_FOUND", "The requested catalog resource was not found", 404)

    @app.errorhandler(413)
    def too_large(_):
        return error_response("REQUEST_TOO_LARGE", "Request body is too large", 413)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5001")), debug=False)
