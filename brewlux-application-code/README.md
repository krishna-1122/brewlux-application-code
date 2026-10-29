# BrewLux — Premium Coffee Shop Application Code

BrewLux is a learning project for a premium coffee shop, organized as Python microservices with a MySQL database and a responsive browser frontend.

## Included in this package

- `frontend/`: HTML, CSS and JavaScript storefront.
- `services/catalog_service/`: Flask catalog API with search, categories, product detail and inventory-aware product listing.
- `services/order_service/`: Flask order API with order creation, order history lookup and status management.
- `shared/`: shared database connection and response helpers.
- `database/schema.sql`: schema and seed data for MySQL.
- `tests/`: unit tests for core validation and API behaviour.
- `requirements.txt` files for each Python service.

## Deliberately not included

As requested, this ZIP does **not** include Dockerfiles, Docker Compose, Docker Stack YAML, Nginx configuration, Jenkinsfile, SonarQube configuration, or AWS deployment files. We can build those together in the next step.

## Application services

- Catalog API default port: `5001`
- Order API default port: `5002`
- Frontend: open `frontend/index.html` in a browser for the visual mockup. When we add the reverse proxy later, the frontend will call `/api/catalog` and `/api/orders` through the same origin.

## Run the Python APIs locally

Use Python 3.11+.

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r services/catalog_service/requirements.txt
pip install -r services/order_service/requirements.txt
```

Configure the environment variables for each service. Example:

```bash
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_NAME=brewlux
export DB_USER=brewlux_app
export DB_PASSWORD='replace-with-a-local-password'
export CATALOG_SERVICE_URL=http://127.0.0.1:5001
```

Initialize the MySQL database with `database/schema.sql`, then start each service in separate terminals:

```bash
python -m services.catalog_service.app
python -m services.order_service.app
```

For local frontend API calls without a proxy, set `window.BREWLUX_API_BASE` in the browser console to the URL of the relevant API, or we can add a development proxy when we build the container configuration.

## API endpoints

Catalog:
- `GET /health`
- `GET /api/v1/categories`
- `GET /api/v1/products`
- `GET /api/v1/products/<product_id>`
- `GET /api/v1/products?search=latte&category=espresso-bar&sort=price_asc`
- `GET /api/v1/products/featured`

Orders:
- `GET /health`
- `POST /api/v1/orders`
- `GET /api/v1/orders/<order_number>?email=customer@example.com`
- `GET /api/v1/orders?email=customer@example.com`
- `PATCH /api/v1/orders/<order_number>/status` (demo/admin-style endpoint; protect it with authentication before real deployment)

Example order payload:

```json
{
  "customer": {
    "name": "Aarav Sharma",
    "email": "aarav@example.com",
    "phone": "+91 9876543210"
  },
  "delivery": {
    "address": "Flat 12, Example Road, Hyderabad",
    "notes": "Please call on arrival"
  },
  "items": [
    {"product_id": 1, "quantity": 2},
    {"product_id": 3, "quantity": 1}
  ]
}
```

## Important learning notes

- This is a portfolio/learning application, not a finished commerce platform.
- Payment processing is intentionally omitted. Never collect or store card details in this demo.
- The order service calls the catalog service to validate product prices. For production, consider timeouts, retries, idempotency keys, authentication, and an asynchronous event flow.
- The order status endpoint is intentionally simple and must be protected before public use.
- Database schema creation is supplied as SQL; we can later decide how to run it safely during deployment.
- Use environment variables or a secrets manager for credentials. Do not commit real secrets.
- Add database migrations, rate limiting, security headers, structured logs, backups, and integration tests before real commercial use.
