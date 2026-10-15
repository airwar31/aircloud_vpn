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
        await self.connection.execute("PRAGMA foreign_keys = ON")
        await self.connection.execute("PRAGMA busy_timeout = 5000")
        
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
                uuid TEXT,
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
                payment_id TEXT UNIQUE,  -- External payment provider ID
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            -- Payment processing state (for idempotent activation)
            CREATE TABLE IF NOT EXISTS payment_events (
                payment_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                tunnel_type TEXT,
                duration TEXT,
                email TEXT,
                status TEXT DEFAULT 'processing',  -- 'processing', 'completed', 'failed'
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
            CREATE INDEX IF NOT EXISTS idx_payment_events_status ON payment_events(status);
        """)
        
        await self.connection.commit()

        # Migrations: add uuid column if missing (for existing DBs)
        try:
            await self.connection.execute(
                "ALTER TABLE vpn_subscriptions ADD COLUMN uuid TEXT"
            )
            await self.connection.commit()
        except Exception:
            pass  # Column already exists

        # Migration: add subscription_token to users table
        try:
            user_columns = await self._get_table_columns("users")
            if "subscription_token" not in user_columns:
                await self.connection.execute(
                    "ALTER TABLE users ADD COLUMN subscription_token TEXT"
                )
                await self.connection.commit()
                logger.info("Added subscription_token column to users table")
        except Exception as e:
            logger.debug(f"subscription_token migration: {e}")

        # Ensure unique index exists even if column was added in previous version
        try:
            user_columns = await self._get_table_columns("users")
            if "subscription_token" in user_columns:
                await self.connection.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_subscription_token ON users(subscription_token)"
                )
                await self.connection.commit()
        except Exception as e:
            logger.debug(f"subscription_token index migration: {e}")

        # Migration: add payment_id to orders table
        try:
            order_columns = await self._get_table_columns("orders")
            if "payment_id" not in order_columns:
                await self.connection.execute(
                    "ALTER TABLE orders ADD COLUMN payment_id TEXT"
                )
                await self.connection.commit()
                logger.info("Added payment_id column to orders table")
        except Exception as e:
            logger.debug(f"orders.payment_id migration: {e}")

        # Ensure payment_id index is created only when column exists
        try:
            order_columns = await self._get_table_columns("orders")
            if "payment_id" in order_columns:
                await self.connection.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_payment_id ON orders(payment_id)"
                )
                await self.connection.commit()
        except Exception as e:
            logger.debug(f"orders.payment_id index migration: {e}")

        logger.info(f"Database initialized: {self.db_path}")
    
    async def close(self):
        """Close database connection"""
        if self.connection:
            await self.connection.close()
            logger.info("Database connection closed")

    async def _get_table_columns(self, table_name: str) -> set[str]:
        """Return set of column names for SQLite table."""
        if not table_name.isidentifier():
            raise ValueError(f"Invalid table name: {table_name}")
        cursor = await self.connection.execute(f"PRAGMA table_info({table_name})")
        rows = await cursor.fetchall()
        return {row["name"] for row in rows}
    
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

    async def generate_subscription_token(self, user_id: int) -> Optional[str]:
        """
        Generate unique subscription token for user

        Args:
            user_id: Telegram user ID

        Returns:
            Generated subscription token or None if error
        """
        import secrets

        try:
            # Generate cryptographically secure random token
            token = secrets.token_urlsafe(16)  # 16 bytes = ~22 chars

            # Update user with token
            await self.connection.execute(
                "UPDATE users SET subscription_token = ? WHERE user_id = ?",
                (token, user_id)
            )
            await self.connection.commit()

            logger.info(f"Generated subscription token for user {user_id}")
            return token
        except Exception as e:
            logger.error(f"Error generating subscription token for user {user_id}: {e}")
            return None

    async def get_subscription_token(self, user_id: int) -> Optional[str]:
        """
        Get subscription token for user (generate if doesn't exist)

        Args:
            user_id: Telegram user ID

        Returns:
            Subscription token or None if error
        """
        try:
            cursor = await self.connection.execute(
                "SELECT subscription_token FROM users WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()

            if row and row["subscription_token"]:
                return row["subscription_token"]

            # Token doesn't exist, generate it
            return await self.generate_subscription_token(user_id)
        except Exception as e:
            logger.error(f"Error getting subscription token for user {user_id}: {e}")
            return None

    async def get_user_by_subscription_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get user by subscription token

        Args:
            token: Subscription token

        Returns:
            User dict or None if not found
        """
        try:
            cursor = await self.connection.execute(
                "SELECT user_id, username, created_at FROM users WHERE subscription_token = ?",
                (token,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting user by subscription token: {e}")
            return None

    # ==================== SUBSCRIPTION OPERATIONS ====================
    
    async def add_vpn_key(
        self,
        user_id: int,
        email: str,
        tunnel_type: str,
        vless_link: str,
        expires_at: float,
        uuid: str = None
    ) -> bool:
        """
        Add VPN subscription for user

        Args:
            user_id: Telegram user ID
            email: Email/identifier for the key (unique)
            tunnel_type: 'single' or 'double'
            vless_link: Complete VLESS URL
            expires_at: Unix timestamp when key expires
            uuid: Xray client UUID

        Returns:
            True if key was added successfully
        """
        try:
            await self.connection.execute(
                """
                INSERT OR REPLACE INTO vpn_subscriptions
                (user_id, email, uuid, tunnel_type, vless_link, expires_at, updated_at, status)
                VALUES (?, ?, ?, ?, ?, datetime(?, 'unixepoch'), CURRENT_TIMESTAMP, 'active')
                """,
                (user_id, email, uuid, tunnel_type, vless_link, expires_at)
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

    async def get_latest_user_key(self, user_id: int, tunnel_type: str) -> Optional[Dict[str, Any]]:
        """Get latest user key by tunnel type (active or expired)."""
        try:
            cursor = await self.connection.execute(
                """
                SELECT *
                FROM vpn_subscriptions
                WHERE user_id = ? AND tunnel_type = ?
                ORDER BY datetime(expires_at) DESC, id DESC
                LIMIT 1
                """,
                (user_id, tunnel_type)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting latest key for user {user_id}/{tunnel_type}: {e}")
            return None

    async def update_key_expiry_timestamp(self, email: str, expires_at_ts: float) -> bool:
        """Set key expiry using Unix timestamp."""
        try:
            await self.connection.execute(
                """
                UPDATE vpn_subscriptions
                SET expires_at = datetime(?, 'unixepoch'), updated_at = CURRENT_TIMESTAMP, status = 'active'
                WHERE email = ?
                """,
                (expires_at_ts, email)
            )
            await self.connection.commit()
            logger.info(f"Key {email} expiry set to ts={expires_at_ts}")
            return True
        except Exception as e:
            logger.error(f"Error updating key expiry for {email}: {e}")
            return False
    
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
        payment_method: str = "pending",
        payment_id: Optional[str] = None
    ) -> Optional[int]:
        """Create new order"""
        try:
            cursor = await self.connection.execute(
                """
                INSERT INTO orders (user_id, amount, plan_type, tunnel_type, payment_method, payment_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, amount, plan_type, tunnel_type, payment_method, payment_id)
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
        """Mark order as completed by order ID"""
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

    async def complete_pending_order(self, user_id: int, tunnel_type: str = None) -> bool:
        """Mark the latest pending order for a user as completed"""
        try:
            query = """
                UPDATE orders
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                WHERE id = (
                    SELECT id FROM orders
                    WHERE user_id = ? AND status = 'pending'
                    {tunnel_filter}
                    ORDER BY created_at DESC LIMIT 1
                )
            """
            if tunnel_type:
                query = query.format(tunnel_filter="AND tunnel_type = ?")
                await self.connection.execute(query, (user_id, tunnel_type))
            else:
                query = query.format(tunnel_filter="")
                await self.connection.execute(query, (user_id,))
            await self.connection.commit()
            logger.info(f"Pending order completed for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error completing pending order: {e}")
            return False

    async def complete_order_by_payment_id(self, payment_id: str) -> bool:
        """Mark order as completed by payment provider ID"""
        try:
            cursor = await self.connection.execute(
                """
                UPDATE orders
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                WHERE payment_id = ? AND status != 'completed'
                """,
                (payment_id,)
            )
            await self.connection.commit()
            if cursor.rowcount > 0:
                logger.info(f"Order completed by payment_id={payment_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error completing order by payment_id={payment_id}: {e}")
            return False

    async def is_payment_processed(self, payment_id: str) -> bool:
        """Check whether payment has already been fully processed"""
        try:
            cursor = await self.connection.execute(
                "SELECT status FROM payment_events WHERE payment_id = ?",
                (payment_id,)
            )
            row = await cursor.fetchone()
            return bool(row and row["status"] == "completed")
        except Exception as e:
            logger.error(f"Error checking processed payment {payment_id}: {e}")
            return False

    async def begin_payment_processing(
        self,
        payment_id: str,
        user_id: int,
        tunnel_type: str,
        duration: str,
        email: str,
    ) -> bool:
        """
        Reserve payment for processing.

        Returns:
            True if current worker can process this payment.
            False if payment is already processing/completed.
        """
        try:
            cursor = await self.connection.execute(
                "SELECT status FROM payment_events WHERE payment_id = ?",
                (payment_id,)
            )
            row = await cursor.fetchone()

            if row:
                status = row["status"]
                if status in ("processing", "completed"):
                    return False

                await self.connection.execute(
                    """
                    UPDATE payment_events
                    SET user_id = ?, tunnel_type = ?, duration = ?, email = ?,
                        status = 'processing', error = NULL, updated_at = CURRENT_TIMESTAMP
                    WHERE payment_id = ?
                    """,
                    (user_id, tunnel_type, duration, email, payment_id)
                )
                await self.connection.commit()
                return True

            await self.connection.execute(
                """
                INSERT INTO payment_events (payment_id, user_id, tunnel_type, duration, email, status)
                VALUES (?, ?, ?, ?, ?, 'processing')
                """,
                (payment_id, user_id, tunnel_type, duration, email)
            )
            await self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error beginning payment processing {payment_id}: {e}")
            return False

    async def finish_payment_processing(self, payment_id: str, success: bool, error: str = None) -> bool:
        """Finalize payment processing state"""
        try:
            status = "completed" if success else "failed"
            await self.connection.execute(
                """
                UPDATE payment_events
                SET status = ?, error = ?, updated_at = CURRENT_TIMESTAMP
                WHERE payment_id = ?
                """,
                (status, error, payment_id)
            )
            await self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error finishing payment processing {payment_id}: {e}")
            return False

    async def get_payment_event(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Get payment processing state and error details."""
        try:
            cursor = await self.connection.execute(
                "SELECT * FROM payment_events WHERE payment_id = ?",
                (payment_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error reading payment event {payment_id}: {e}")
            return None
    
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
