-- Step 1: Create the database
CREATE DATABASE IF NOT EXISTS bus_pass_db;
USE bus_pass_db;

-- Step 2: Create the users table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    address TEXT,
    phone_number VARCHAR(20),
    photo_path VARCHAR(255)
);

-- Step 3: Create the applications table
CREATE TABLE applications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    start_point VARCHAR(100) NOT NULL,
    end_point VARCHAR(100) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('PENDING', 'PAID', 'APPROVED', 'REJECTED') DEFAULT 'PENDING',
    payment_status ENUM('PENDING', 'COMPLETED', 'FAILED') DEFAULT 'PENDING',
    pass_number VARCHAR(50) UNIQUE,
    qr_code_path VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Step 4: Create the admin table
CREATE TABLE admin_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL
);

-- Step 5: Insert test admin (password: adminpass)
INSERT INTO admin_users (username, password_hash)
VALUES ('admin', 'adminpass');