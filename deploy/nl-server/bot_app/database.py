"""
Database layer for AirCloud VPN Bot
SQLite3 with aiosqlite for async operations
"""

import aiosqlite
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class Database:
    """Database manager for VPN bot"""
    
    def __init__(self, db_path: str = "./data/users.db"):
        """
        Initialize database
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.connection: Optional[aiosqlite.Connection] = None
    
    async def init(self):
        """Initialize database tables"""
        self.connection = await aiosqlite.connect(self.db_path)
        self.connection.row_factory = aiosqlite.Row
        
        # Create tables
        await self.connection.executescript("""
            -- Users table
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                balance REAL DEFAULT 0.0,
                status TEXT DEFAULT 'active'
            );
            
            -- VPN Subscriptions
            CREATE TABLE IF NOT EXISTS vpn_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                email TEXT UNIQUE NOT NULL,
                tunnel_type TEXT NOT NULL,  -- 'single' or 'double'
                vless_link TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                UNIQUE(user_id, tunnel_type, email)
            );
            
            -- VPN Keys (old format - for compatibility)
            CREATE TABLE IF NOT EXISTS vpn_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                key TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );
            
            -- Orders/Payments
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                plan_type TEXT NOT NULL,  -- '1_month', '3_months', '12_months'
                tunnel_type TEXT NOT NULL,  -- 'single' or 'double'
                status TEXT DEFAULT 'pending',  -- 'pending', 'completed', 'failed'
                payment_method TEXT,  -- 'crypto', 'stripe', 'paypal'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );
            
            -- Gifts
            CREATE TABLE IF NOT EXISTS gifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gift_code TEXT UNIQUE NOT NULL,
                created_by INTEGER NOT NULL,
                tunnel_type TEXT NOT NULL,  -- 'single' or 'double'
                days INTEGER NOT NULL,
                status TEXT DEFAULT 'active',  -- 'active', 'used', 'expired'
                used_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_at TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY(created_by) REFERENCES users(user_id),
                FOREIGN KEY(used_by) REFERENCES users(user_id)
            );
            
            -- Admin logs
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(admin_id) REFERENCES users(user_id)
            );
            
            -- Create indexes for faster queries
            CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at);
            CREATE INDEX IF NOT EXISTS idx_vpn_subscriptions_user ON vpn_subscriptions(user_id);
            CREATE INDEX IF NOT EXISTS idx_vpn_subscriptions_expires ON vpn_subscriptions(expires_at);
            CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
            CREATE INDEX IF NOT EXISTS idx_gifts_code ON gifts(gift_code);
            CREATE INDEX IF NOT EXISTS idx_gifts_created_by ON gifts(created_by);
        """)
        
        await self.connection.commit()
        logger.info(f"Database initialized: {self.db_path}")
    
    async def close(self):
        """Close database connection"""
        if self.connection:
            await self.connection.close()
            logger.info("Database connection closed")
    
    # ==================== USER OPERATIONS ====================
    
    async def add_user(self, user_id: int, username: str) -> bool:
        """
        Add new user or update existing
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
        
        Returns:
            True if user was added/updated, False otherwise
        """
        try:
            cursor = await self.connection.execute(
                """
                INSERT OR IGNORE INTO users (user_id, username)
                VALUES (?, ?)
                """,
                (user_id, username)
            )
            await self.connection.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"User {user_id} ({username}) added")
                return True
            
            # Update username if user exists
            await self.connection.execute(
                "UPDATE users SET username = ? WHERE user_id = ?",
                (username, user_id)
            )
            await self.connection.commit()
            return False
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")
            return False
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            cursor = await self.connection.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users"""
        try:
            cursor = await self.connection.execute(
                "SELECT user_id, username, created_at, balance FROM users ORDER BY created_at DESC"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    async def update_user_balance(self, user_id: int, amount: float) -> bool:
        """Update user balance"""
        try:
            await self.connection.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (amount, user_id)
            )
            await self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating user balance: {e}")
            return False
    
    # ==================== SUBSCRIPTION OPERATIONS ====================
    
    async def add_vpn_key(
        self,
        user_id: int,
        email: str,
        tunnel_type: str,
        vless_link: str,
        expires_at: float
    ) -> bool:
        """
        Add VPN subscription for user
        
        Args:
            user_id: Telegram user ID
            email: Email/identifier for the key (unique)
            tunnel_type: 'single' or 'double'
            vless_link: Complete VLESS URL
            expires_at: Unix timestamp when key expires
        
        Returns:
            True if key was added successfully
        """
        try:
            await self.connection.execute(
                """
                INSERT OR REPLACE INTO vpn_subscriptions 
                (user_id, email, tunnel_type, vless_link, expires_at, updated_at, status)
                VALUES (?, ?, ?, ?, datetime(?, 'unixepoch'), CURRENT_TIMESTAMP, 'active')
                """,
                (user_id, email, tunnel_type, vless_link, expires_at)
            )
            await self.connection.commit()
            logger.info(f"VPN key added for user {user_id}: {email}")
            return True
        except sqlite3.IntegrityError as e:
            logger.error(f"Key already exists or constraint violation: {e}")
            return False
        except Exception as e:
            logger.error(f"Error adding VPN key: {e}")
            return False
    
    async def get_user_keys(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all active VPN keys for user"""
        try:
            cursor = await self.connection.execute(
                """
                SELECT id, email, tunnel_type, vless_link, expires_at, created_at, status
                FROM vpn_subscriptions
                WHERE user_id = ? AND status = 'active' AND datetime(expires_at) > CURRENT_TIMESTAMP
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                d = dict(row)
                # Convert expires_at to Unix timestamp
                d['expires_at'] = datetime.fromisoformat(d['expires_at']).timestamp()
                result.append(d)
            return result
        except Exception as e:
            logger.error(f"Error getting user keys: {e}")
            return []
    
    async def get_key_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get VPN key by email"""
        try:
            cursor = await self.connection.execute(
                "SELECT * FROM vpn_subscriptions WHERE email = ?",
                (email,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting key by email: {e}")
            return None
    
    async def update_key_expiry(self, email: str, days: int) -> bool:
        """Update key expiry date"""
        try:
            expires_at = datetime.now() + timedelta(days=days)
            await self.connection.execute(
                """
                UPDATE vpn_subscriptions 
                SET expires_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE email = ?
                """,
                (expires_at.isoformat(), email)
            )
            await self.connection.commit()
            logger.info(f"Key {email} expiry updated to {days} days")
            return True
        except Exception as e:
            logger.error(f"Error updating key expiry: {e}")
            return False
    
    async def revoke_key(self, email: str) -> bool:
        """Deactivate VPN key"""
        try:
            await self.connection.execute(
                "UPDATE vpn_subscriptions SET status = 'revoked' WHERE email = ?",
                (email,)
            )
            await self.connection.commit()
            logger.info(f"Key {email} revoked")
            return True
        except Exception as e:
            logger.error(f"Error revoking key: {e}")
            return False
    
    async def get_expired_keys(self) -> List[Dict[str, Any]]:
        """Get all expired keys"""
        try:
            cursor = await self.connection.execute(
                """
                SELECT email, user_id, tunnel_type FROM vpn_subscriptions
                WHERE status = 'active' AND datetime(expires_at) <= CURRENT_TIMESTAMP
                """
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting expired keys: {e}")
            return []
    
    async def cleanup_expired_keys(self) -> int:
        """Mark expired keys as expired"""
        try:
            cursor = await self.connection.execute(
                """
                UPDATE vpn_subscriptions
                SET status = 'expired'
                WHERE status = 'active' AND datetime(expires_at) <= CURRENT_TIMESTAMP
                """
            )
            await self.connection.commit()
            count = cursor.rowcount
            logger.info(f"Cleaned up {count} expired keys")
            return count
        except Exception as e:
            logger.error(f"Error cleaning up expired keys: {e}")
            return 0
    
    # ==================== ORDER OPERATIONS ====================
    
    async def create_order(
        self,
        user_id: int,
        amount: float,
        plan_type: str,
        tunnel_type: str,
        payment_method: str = "pending"
    ) -> Optional[int]:
        """Create new order"""
        try:
            cursor = await self.connection.execute(
                """
                INSERT INTO orders (user_id, amount, plan_type, tunnel_type, payment_method)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, amount, plan_type, tunnel_type, payment_method)
            )
            await self.connection.commit()
            order_id = cursor.lastrowid
            logger.info(f"Order {order_id} created for user {user_id}")
            return order_id
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None
    
    async def get_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Get order by ID"""
        try:
            cursor = await self.connection.execute(
                "SELECT * FROM orders WHERE id = ?",
                (order_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting order: {e}")
            return None
    
    async def complete_order(self, order_id: int) -> bool:
        """Mark order as completed"""
        try:
            await self.connection.execute(
                """
                UPDATE orders 
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (order_id,)
            )
            await self.connection.commit()
            logger.info(f"Order {order_id} completed")
            return True
        except Exception as e:
            logger.error(f"Error completing order: {e}")
            return False
    
    # ==================== GIFT OPERATIONS ====================
    
    async def create_gift(
        self,
        created_by: int,
        gift_code: str,
        tunnel_type: str,
        days: int
    ) -> bool:
        """Create gift code"""
        try:
            expires_at = datetime.now() + timedelta(days=30)  # Gift expires in 30 days
            await self.connection.execute(
                """
                INSERT INTO gifts (created_by, gift_code, tunnel_type, days, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (created_by, gift_code, tunnel_type, days, expires_at.isoformat())
            )
            await self.connection.commit()
            logger.info(f"Gift {gift_code} created by {created_by}")
            return True
        except Exception as e:
            logger.error(f"Error creating gift: {e}")
            return False
    
    async def get_gift(self, gift_code: str) -> Optional[Dict[str, Any]]:
        """Get gift by code"""
        try:
            cursor = await self.connection.execute(
                "SELECT * FROM gifts WHERE gift_code = ?",
                (gift_code,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting gift: {e}")
            return None
    
    async def use_gift(self, gift_code: str, user_id: int) -> bool:
        """Mark gift as used by user"""
        try:
            await self.connection.execute(
                """
                UPDATE gifts
                SET status = 'used', used_by = ?, used_at = CURRENT_TIMESTAMP
                WHERE gift_code = ?
                """,
                (user_id, gift_code)
            )
            await self.connection.commit()
            logger.info(f"Gift {gift_code} used by user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error using gift: {e}")
            return False
    
    async def get_user_gifts(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all gifts created by user"""
        try:
            cursor = await self.connection.execute(
                """
                SELECT gift_code, tunnel_type, days, status, created_at, used_by, used_at
                FROM gifts
                WHERE created_by = ?
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting user gifts: {e}")
            return []
    
    # ==================== STATISTICS ====================
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            # User count
            cursor = await self.connection.execute("SELECT COUNT(*) as count FROM users")
            user_count = (await cursor.fetchone())['count']
            
            # Active subscriptions
            cursor = await self.connection.execute(
                "SELECT COUNT(*) as count FROM vpn_subscriptions WHERE status = 'active'"
            )
            active_keys = (await cursor.fetchone())['count']
            
            # Total orders
            cursor = await self.connection.execute("SELECT COUNT(*) as count FROM orders")
            order_count = (await cursor.fetchone())['count']
            
            # Total revenue
            cursor = await self.connection.execute(
                "SELECT COALESCE(SUM(amount), 0) as total FROM orders WHERE status = 'completed'"
            )
            revenue = (await cursor.fetchone())['total']
            
            # Active gifts
            cursor = await self.connection.execute(
                "SELECT COUNT(*) as count FROM gifts WHERE status = 'active'"
            )
            active_gifts = (await cursor.fetchone())['count']
            
            return {
                'total_users': user_count,
                'active_subscriptions': active_keys,
                'total_orders': order_count,
                'total_revenue': revenue,
                'active_gifts': active_gifts
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
    
    # ==================== ADMIN OPERATIONS ====================
    
    async def log_admin_action(self, admin_id: int, action: str, details: str = None) -> bool:
        """Log admin action"""
        try:
            await self.connection.execute(
                "INSERT INTO admin_logs (admin_id, action, details) VALUES (?, ?, ?)",
                (admin_id, action, details)
            )
            await self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error logging admin action: {e}")
            return False
    
    async def get_admin_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent admin logs"""
        try:
            cursor = await self.connection.execute(
                """
                SELECT admin_id, action, details, created_at FROM admin_logs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting admin logs: {e}")
            return []
