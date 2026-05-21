import pymysql
from pymysql.cursors import DictCursor
import pandas as pd
from datetime import datetime, timedelta
from .config import DB_CONFIG
from .utils import logger

class StockDB:
    def __init__(self):
        self.connection = None
        self._connect()
        self._init_tables()

    def _connect(self):
        """连接数据库"""
        try:
            self.connection = pymysql.connect(
                host=DB_CONFIG["host"],
                port=DB_CONFIG["port"],
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"],
                database=DB_CONFIG["database"],
                charset="utf8mb4",
                cursorclass=DictCursor,
                use_unicode=True
            )
            logger.info("✅ 数据库连接成功")
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {str(e)}")
            raise

    def _init_tables(self):
        """初始化表"""
        with self.connection.cursor() as cursor:
            # 股票基本信息
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_basic (
                code VARCHAR(20) PRIMARY KEY,
                name VARCHAR(50) NOT NULL,
                last_update DATE,
                INDEX idx_last_update (last_update)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # 日线数据
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_daily (
                id INT AUTO_INCREMENT PRIMARY KEY,
                code VARCHAR(20) NOT NULL,
                trade_date DATE NOT NULL,
                open DECIMAL(10,2) NOT NULL,
                high DECIMAL(10,2) NOT NULL,
                low DECIMAL(10,2) NOT NULL,
                close DECIMAL(10,2) NOT NULL,
                volume BIGINT NOT NULL,
                UNIQUE KEY uk_code_date (code, trade_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            self.connection.commit()

    def get_stock_list(self):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT code, name, last_update FROM stock_basic")
            return cursor.fetchall()

    def update_stock_list(self, stock_list):
        with self.connection.cursor() as cursor:
            for code, name in stock_list:
                cursor.execute("""
                INSERT INTO stock_basic (code, name, last_update)
                VALUES (%s, %s, NULL)
                ON DUPLICATE KEY UPDATE name=%s
                """, (code, name, name))
            self.connection.commit()

    def get_last_trade_date(self, code):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT MAX(trade_date) as last_date FROM stock_daily WHERE code=%s", (code,))
            res = cursor.fetchone()
            return res["last_date"] if res else None

    def insert_daily_data(self, code, df):
        if df.empty:
            return

        # 👇 关键修复：删除所有包含空值/NAN的行，MySQL不识别NaN
        df = df.dropna()

        data = []
        for _, row in df.iterrows():
            data.append((
                code,
                row["date"],
                row["open"],
                row["high"],
                row["low"],
                row["close"],
                row["volume"]
            ))

        with self.connection.cursor() as cursor:
            cursor.executemany("""
                INSERT IGNORE INTO stock_daily
                (code, trade_date, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, data)
            self.connection.commit()

    def get_daily_data(self, code, days=60):
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT trade_date as date, open, high, low, close, volume
                FROM stock_daily
                WHERE code=%s
                ORDER BY trade_date DESC LIMIT %s
            """, (code, days))
            data = cursor.fetchall()
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            # 👇 修复：把 Decimal 全部转成 float
            for col in ['open', 'high', 'low', 'close']:
                df[col] = df[col].astype(float)
            
            df = df.sort_values("date").reset_index(drop=True)
            return df

    def update_last_update(self, code):
        with self.connection.cursor() as cursor:
            cursor.execute("UPDATE stock_basic SET last_update=CURDATE() WHERE code=%s", (code,))
            self.connection.commit()

    def close(self):
        if self.connection:
            self.connection.close()
            logger.info("✅ 数据库连接已关闭")