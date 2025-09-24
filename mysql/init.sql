-- Инициализация базы данных VPN бота
CREATE DATABASE IF NOT EXISTS vpn_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE vpn_bot;

-- Таблица пользователей
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица заказов
CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    plan_id VARCHAR(50) NOT NULL,
    payment_id VARCHAR(255) UNIQUE NOT NULL,
    amount INT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
);

-- Таблица VPN ключей
CREATE TABLE vpn_keys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    order_id INT,
    email VARCHAR(255) UNIQUE NOT NULL,
    config TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    traffic_limit BIGINT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_hidden BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(telegram_id),
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- Таблица рефералов
CREATE TABLE referrals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    referrer_id BIGINT NOT NULL,
    referred_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (referrer_id) REFERENCES users(telegram_id),
    FOREIGN KEY (referred_id) REFERENCES users(telegram_id)
);

-- Таблица реферальных выплат
CREATE TABLE referral_earnings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    referrer_id BIGINT NOT NULL,
    referred_id BIGINT NOT NULL,
    order_id INT NOT NULL,
    plan_id VARCHAR(50) NOT NULL,
    amount INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (referrer_id) REFERENCES users(telegram_id),
    FOREIGN KEY (referred_id) REFERENCES users(telegram_id),
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- Таблица подарочных ссылок
CREATE TABLE gift_links (
    id INT AUTO_INCREMENT PRIMARY KEY,
    gift_code VARCHAR(255) UNIQUE NOT NULL,
    days INT NOT NULL,
    used_by BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP NULL,
    FOREIGN KEY (used_by) REFERENCES users(telegram_id)
);

-- Таблица уведомлений
CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    message TEXT NOT NULL,
    sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
);

-- Таблица согласий с пользовательским соглашением
CREATE TABLE user_agreements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    agreed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
);

-- Индексы для оптимизации
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_payment_id ON orders(payment_id);
CREATE INDEX idx_vpn_keys_user_id ON vpn_keys(user_id);
CREATE INDEX idx_vpn_keys_expires_at ON vpn_keys(expires_at);
CREATE INDEX idx_referrals_referrer_id ON referrals(referrer_id);
CREATE INDEX idx_gift_links_code ON gift_links(gift_code);
CREATE INDEX idx_user_agreements_user_id ON user_agreements(user_id);