CREATE DATABASE IF NOT EXISTS retail_db;
USE retail_db;

CREATE TABLE IF NOT EXISTS customers (
    id INT UNSIGNED NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY customers_email_unique (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS products (
    id INT UNSIGNED NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    description TEXT,
    price DECIMAL(12, 2) NOT NULL,
    ram VARCHAR(50),
    rating DECIMAL(3, 2),
    stock INT UNSIGNED,
    delivery_days INT UNSIGNED,
    warranty_months INT UNSIGNED,
    brand VARCHAR(100),
    sku VARCHAR(100),
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY products_sku_unique (sku)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS orders (
    id INT UNSIGNED NOT NULL,
    customer_id INT UNSIGNED NOT NULL,
    status VARCHAR(32) NOT NULL,
    total_amount DECIMAL(12, 2) NOT NULL,
    tracking_number VARCHAR(100),
    shipping_address TEXT,
    priority VARCHAR(32),
    notes TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    KEY orders_customer_id_index (customer_id),
    CONSTRAINT orders_customer_id_foreign
        FOREIGN KEY (customer_id) REFERENCES customers (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS order_items (
    id INT UNSIGNED NOT NULL,
    order_id INT UNSIGNED NOT NULL,
    product_id INT UNSIGNED NOT NULL,
    quantity INT UNSIGNED NOT NULL,
    unit_price DECIMAL(12, 2) NOT NULL,
    PRIMARY KEY (id),
    KEY order_items_order_id_index (order_id),
    KEY order_items_product_id_index (product_id),
    CONSTRAINT order_items_order_id_foreign
        FOREIGN KEY (order_id) REFERENCES orders (id),
    CONSTRAINT order_items_product_id_foreign
        FOREIGN KEY (product_id) REFERENCES products (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
