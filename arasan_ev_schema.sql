-- Arasan EV Showroom Management System Database Schema
-- MySQL 8.0+ with InnoDB Engine

CREATE DATABASE IF NOT EXISTS arasan;
USE arasan;

-- Users table (for authentication and roles)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('customer', 'manager', 'admin') DEFAULT 'customer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Customers table
CREATE TABLE customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    phone VARCHAR(15),
    address TEXT,
    city VARCHAR(50),
    state VARCHAR(50),
    pincode VARCHAR(10),
    dob DATE,
    gender ENUM('male', 'female', 'other'),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Suppliers table
CREATE TABLE suppliers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    contact_name VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(15),
    address TEXT,
    city VARCHAR(50),
    state VARCHAR(50),
    gstin VARCHAR(15),
    payment_terms VARCHAR(50) DEFAULT '30 days',
    rating DECIMAL(2,1) DEFAULT 5.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vehicles table
CREATE TABLE vehicles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    make VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    year INT NOT NULL,
    category ENUM('sedan', 'hatchback', 'suv', 'truck', 'van', 'coupe') DEFAULT 'sedan',
    range_km INT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    stock INT DEFAULT 0,
    status ENUM('available', 'reserved', 'sold') DEFAULT 'available',
    image_url VARCHAR(255),
    color VARCHAR(30),
    battery_capacity_kwh DECIMAL(5,1),
    charging_time_hrs DECIMAL(3,1),
    top_speed_kmh INT,
    warranty_years INT DEFAULT 3,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inventory table
CREATE TABLE inventory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_id INT NOT NULL,
    warehouse_location VARCHAR(100) DEFAULT 'Main Warehouse',
    stock INT DEFAULT 0,
    min_stock INT DEFAULT 1,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
);

-- Bookings table (test drive bookings)
CREATE TABLE bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    vehicle_id INT NOT NULL,
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scheduled_for DATETIME,
    status ENUM('pending', 'confirmed', 'completed', 'cancelled') DEFAULT 'pending',
    note TEXT,
    test_drive_location VARCHAR(255),
    preferred_contact VARCHAR(50),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
);

-- Sales Order table
CREATE TABLE sales_order (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_no VARCHAR(20) UNIQUE NOT NULL,
    customer_id INT,
    vehicle_id INT NOT NULL,
    qty INT DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    discount DECIMAL(10,2) DEFAULT 0,
    payment_method ENUM('cash', 'card', 'upi', 'bank_transfer', 'emi') DEFAULT 'cash',
    status ENUM('pending', 'confirmed', 'completed', 'cancelled') DEFAULT 'pending',
    sales_person VARCHAR(100),
    emi_months INT DEFAULT 0,
    sold_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
);

-- Purchase Order table
CREATE TABLE purchase_order (
    id INT AUTO_INCREMENT PRIMARY KEY,
    purchase_no VARCHAR(20) UNIQUE NOT NULL,
    supplier_id INT,
    vehicle_id INT NOT NULL,
    qty INT NOT NULL,
    unit_cost DECIMAL(10,2) NOT NULL,
    total_cost DECIMAL(10,2) NOT NULL,
    status ENUM('ordered', 'received', 'partially_received', 'cancelled') DEFAULT 'ordered',
    expected_delivery DATE,
    ordered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    received_at TIMESTAMP NULL,
    notes TEXT,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
);

-- Invoices table
CREATE TABLE invoices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_no VARCHAR(20) UNIQUE NOT NULL,
    order_id INT NOT NULL,
    customer_id INT,
    sub_total DECIMAL(10,2) NOT NULL,
    tax DECIMAL(10,2) DEFAULT 0,
    total DECIMAL(10,2) NOT NULL,
    status ENUM('draft', 'issued', 'paid', 'overdue') DEFAULT 'draft',
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    due_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL 30 DAY),
    FOREIGN KEY (order_id) REFERENCES sales_order(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
);

-- Bills table
CREATE TABLE bills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bill_no VARCHAR(20) UNIQUE NOT NULL,
    supplier_id INT,
    purchase_id INT,
    amount DECIMAL(10,2) NOT NULL,
    status ENUM('unpaid', 'paid', 'overdue') DEFAULT 'unpaid',
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    due_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL 30 DAY),
    paid_at TIMESTAMP NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL,
    FOREIGN KEY (purchase_id) REFERENCES purchase_order(id) ON DELETE CASCADE
);

-- Reports table (for tracking report generations)
CREATE TABLE reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_type VARCHAR(50) NOT NULL,
    generated_by INT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (generated_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes for better performance
CREATE INDEX idx_vehicles_make_model ON vehicles(make, model);
CREATE INDEX idx_vehicles_category ON vehicles(category);
CREATE INDEX idx_vehicles_status ON vehicles(status);
CREATE INDEX idx_sales_order_customer ON sales_order(customer_id);
CREATE INDEX idx_sales_order_vehicle ON sales_order(vehicle_id);
CREATE INDEX idx_sales_order_status ON sales_order(status);
CREATE INDEX idx_purchase_order_supplier ON purchase_order(supplier_id);
CREATE INDEX idx_purchase_order_status ON purchase_order(status);
CREATE INDEX idx_invoices_customer ON invoices(customer_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_bills_supplier ON bills(supplier_id);
CREATE INDEX idx_bills_status ON bills(status);
CREATE INDEX idx_bookings_user ON bookings(user_id);
CREATE INDEX idx_bookings_status ON bookings(status);

-- Sample data (optional - remove in production)
INSERT INTO users (username, password, role) VALUES
('admin', 'admin123', 'admin'),
('manager', 'manager123', 'manager'),
('customer1', 'pass123', 'customer');

INSERT INTO customers (user_id, name, email, phone, city) VALUES
(3, 'John Doe', 'john@example.com', '9876543210', 'Chennai');

INSERT INTO suppliers (name, email, phone, city) VALUES
('Tesla India', 'contact@tesla.in', '1800-123-456', 'Mumbai'),
('Nissan India', 'sales@nissan.in', '1800-456-789', 'Delhi');

INSERT INTO vehicles (make, model, year, category, range_km, price, stock, status) VALUES
('Tesla', 'Model 3', 2024, 'sedan', 575, 5500000.00, 5, 'available'),
('Nissan', 'Leaf', 2024, 'hatchback', 385, 3500000.00, 3, 'available'),
('Tesla', 'Model Y', 2024, 'suv', 514, 6500000.00, 2, 'available');