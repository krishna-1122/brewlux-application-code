CREATE DATABASE IF NOT EXISTS brewlux CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE brewlux;

CREATE TABLE IF NOT EXISTS categories (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(80) NOT NULL UNIQUE,
    slug VARCHAR(90) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    category_id BIGINT UNSIGNED NULL,
    sku VARCHAR(40) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL,
    slug VARCHAR(140) NOT NULL UNIQUE,
    description TEXT,
    origin VARCHAR(100),
    roast_level ENUM('LIGHT','MEDIUM','DARK') NOT NULL DEFAULT 'MEDIUM',
    price DECIMAL(10,2) NOT NULL,
    image_url VARCHAR(500),
    available BOOLEAN NOT NULL DEFAULT TRUE,
    featured BOOLEAN NOT NULL DEFAULT FALSE,
    stock_quantity INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_products_category FOREIGN KEY (category_id) REFERENCES categories(id),
    CONSTRAINT chk_products_price CHECK (price >= 0),
    CONSTRAINT chk_products_stock CHECK (stock_quantity >= 0),
    INDEX idx_products_category (category_id),
    INDEX idx_products_available (available),
    FULLTEXT INDEX ft_products_search (name, description, origin)
);

CREATE TABLE IF NOT EXISTS orders (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    order_number VARCHAR(40) NOT NULL UNIQUE,
    customer_name VARCHAR(150) NOT NULL,
    customer_email VARCHAR(254) NOT NULL,
    customer_phone VARCHAR(30),
    delivery_address VARCHAR(500),
    notes VARCHAR(500),
    status ENUM('PENDING','CONFIRMED','PREPARING','READY','COMPLETED','CANCELLED') NOT NULL DEFAULT 'PENDING',
    subtotal DECIMAL(10,2) NOT NULL,
    tax_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_orders_email (customer_email),
    INDEX idx_orders_status_created (status, created_at)
);

CREATE TABLE IF NOT EXISTS order_items (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT UNSIGNED NOT NULL,
    product_id BIGINT UNSIGNED NOT NULL,
    product_name VARCHAR(120) NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    line_total DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    CONSTRAINT chk_order_items_quantity CHECK (quantity > 0),
    INDEX idx_order_items_order (order_id)
);

INSERT IGNORE INTO categories (id, name, slug, description) VALUES
(1, 'Espresso Bar', 'espresso-bar', 'Classic espresso-based coffee drinks'),
(2, 'Signature Coffee', 'signature-coffee', 'House signatures and indulgent favourites'),
(3, 'Cold Coffee', 'cold-coffee', 'Chilled coffee crafted for slow afternoons'),
(4, 'Coffee Beans', 'coffee-beans', 'Beans for your home brewing ritual');

INSERT IGNORE INTO products
(id, category_id, sku, name, slug, description, origin, roast_level, price, image_url, available, featured, stock_quantity)
VALUES
(1, 1, 'BRW-ESP-001', 'Velvet Espresso', 'velvet-espresso', 'A concentrated shot with dark chocolate, toasted almond and a lingering caramel finish.', 'Chikmagalur, India', 'DARK', 180.00, 'https://images.unsplash.com/photo-1510707577719-ae7c14805e3a?auto=format&fit=crop&w=900&q=85', TRUE, TRUE, 100),
(2, 1, 'BRW-CAP-002', 'Silk Cappuccino', 'silk-cappuccino', 'Balanced espresso under a cloud of microfoam, finished with cocoa dust.', 'Coorg, India', 'MEDIUM', 220.00, 'https://images.unsplash.com/photo-1572442388796-11668a67e53d?auto=format&fit=crop&w=900&q=85', TRUE, TRUE, 100),
(3, 1, 'BRW-LAT-003', 'Golden Hour Latte', 'golden-hour-latte', 'Sweet, smooth espresso and steamed milk with a delicate caramel note.', 'Bababudangiri, India', 'MEDIUM', 240.00, 'https://images.unsplash.com/photo-1461023058943-07fcbe16d735?auto=format&fit=crop&w=900&q=85', TRUE, TRUE, 100),
(4, 2, 'BRW-MOC-004', 'Midnight Mocha', 'midnight-mocha', 'Deep cocoa meets rich espresso for a velvety, dessert-like cup.', 'Araku Valley, India', 'DARK', 260.00, 'https://images.unsplash.com/photo-1578314675249-a6910f80cc4e?auto=format&fit=crop&w=900&q=85', TRUE, TRUE, 70),
(5, 3, 'BRW-CBR-005', 'Slow Bloom Cold Brew', 'slow-bloom-cold-brew', 'A 16-hour steep creates a mellow, low-acidity and naturally sweet finish.', 'Chikmagalur, India', 'MEDIUM', 280.00, 'https://images.unsplash.com/photo-1517701604599-bb29b5650907?auto=format&fit=crop&w=900&q=85', TRUE, TRUE, 65),
(6, 4, 'BRW-BEAN-006', 'Monsoon Estate Beans', 'monsoon-estate-beans', 'A 250 g bag with nutty sweetness, gentle spice and a full-bodied finish.', 'Western Ghats, India', 'MEDIUM', 520.00, 'https://images.unsplash.com/photo-1559525839-b184a4d698c7?auto=format&fit=crop&w=900&q=85', TRUE, FALSE, 40),
(7, 2, 'BRW-VAN-007', 'Vanilla Cloud Latte', 'vanilla-cloud-latte', 'A soft vanilla aroma meets a double espresso and creamy milk.', 'Coorg, India', 'MEDIUM', 270.00, 'https://images.unsplash.com/photo-1536935338788846bb9981813?auto=format&fit=crop&w=900&q=85', TRUE, FALSE, 55),
(8, 3, 'BRW-ICED-008', 'Iced Brown Sugar Shaker', 'iced-brown-sugar-shaker', 'Espresso shaken over ice with brown sugar and a bright finish.', 'Araku Valley, India', 'DARK', 250.00, 'https://images.unsplash.com/photo-1461023058943-07fcbe16d735?auto=format&fit=crop&w=900&q=85', TRUE, FALSE, 60);
