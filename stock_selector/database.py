import mysql.connector
# 修复：正确的DictCursor导入路径
from mysql.connector import DictCursor
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
        """连接数据库（使用官方驱动，无编码问题）"""
        try:
            self.connection = mysql.connector.connect(
                host=DB_CONFIG['host'],
                port=DB_CONFIG['port'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                database=DB_CONFIG['database'],
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci',
                use_unicode=True,
                autocommit=False
            )
            
            # 逐条执行编码设置
            cursor = self.connection.cursor()
            cursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute("SET character_set_client=utf8mb4")
            cursor.execute("SET character_set_connection=utf8mb4")
            cursor.execute("SET character_set_results=utf8mb4")
            cursor.close()
            
            logger.info("✅ 数据库连接成功")
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {str(e)}")
            raise
    
    def _init_tables(self):
        """初始化数据库表"""
        with self.connection.cursor() as cursor:
            # 股票基本信息表
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_basic (
                code VARCHAR(20) NOT NULL COMMENT '股票代码',
                name VARCHAR(50) NOT NULL COMMENT '股票名称',
                last_update DATE DEFAULT NULL COMMENT '最后更新日期',
                create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (code),
                INDEX idx_last_update (last_update)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)
            
            # 股票日线数据表
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_daily (
                id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
                code VARCHAR(20) NOT NULL COMMENT '股票代码',
                trade_date DATE NOT NULL COMMENT '交易日期',
                open DECIMAL(10,2) NOT NULL COMMENT '开盘价',
                high DECIMAL(10,2) NOT NULL COMMENT '最高价',
                low DECIMAL(10,2) NOT NULL COMMENT '最低价',
                close DECIMAL(10,2) NOT NULL COMMENT '收盘价',
                pre_close DECIMAL(10,2) DEFAULT NULL COMMENT '前收盘价',
                volume BIGINT NOT NULL COMMENT '成交量',
                amount BIGINT DEFAULT NULL COMMENT '成交额',
                turn DECIMAL(6,2) DEFAULT NULL COMMENT '换手率',
                create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_code_date (code, trade_date),
                INDEX idx_code (code),
                INDEX idx_trade_date (trade_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)
            
            # 选股结果历史表
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_screen_result (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                screen_date DATE NOT NULL COMMENT '选股日期',
                code VARCHAR(20) NOT NULL COMMENT '股票代码',
                name VARCHAR(50) NOT NULL COMMENT '股票名称',
                close_price DECIMAL(10,2) NOT NULL COMMENT '收盘价',
                strategy_name VARCHAR(50) DEFAULT 'default',
                create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_date_code_strategy (screen_date, code, strategy_name),
                INDEX idx_screen_date (screen_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)
            
            self.connection.commit()
    
    def get_stock_list(self):
        """获取所有股票列表"""
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT code, name, last_update FROM stock_basic")
            return cursor.fetchall()
    
    def update_stock_list(self, stock_list):
        """更新股票基本信息"""
        with self.connection.cursor() as cursor:
            for code, name in stock_list:
                cursor.execute("""
                INSERT INTO stock_basic (code, name, last_update)
                VALUES (%s, %s, NULL)
                ON DUPLICATE KEY UPDATE name=%s
                """, (code, name, name))
            self.connection.commit()
        logger.info(f"✅ 股票列表更新完成，共 {len(stock_list)} 只")
    
    def get_last_trade_date(self, code):
        """获取股票最新交易日期"""
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute("""
            SELECT MAX(trade_date) as last_date FROM stock_daily WHERE code=%s
            """, (code,))
            result = cursor.fetchone()
            return result['last_date'] if result['last_date'] else None
    
    def insert_daily_data(self, code, df):
        """批量插入日线数据"""
        if df.empty:
            return
        
        data = []
        for _, row in df.iterrows():
            data.append((
                code,
                row['date'],
                row['open'],
                row['high'],
                row['low'],
                row['close'],
                row.get('preclose', None),
                row['volume'],
                row.get('amount', None),
                row.get('turn', None)
            ))
        
        with self.connection.cursor() as cursor:
            cursor.executemany("""
            INSERT IGNORE INTO stock_daily 
            (code, trade_date, open, high, low, close, pre_close, volume, amount, turn)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, data)
            self.connection.commit()
    
    def get_daily_data(self, code, days=60):
        """获取最近N天的日线数据"""
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute("""
            SELECT trade_date as date, open, high, low, close, volume
            FROM stock_daily 
            WHERE code=%s
            ORDER BY trade_date DESC
            LIMIT %s
            """, (code, days))
            
            result = cursor.fetchall()
            if not result:
                return pd.DataFrame()
            
            df = pd.DataFrame(result)
            return df.sort_values('date').reset_index(drop=True)
    
    def update_last_update(self, code):
        """更新股票最后更新时间"""
        with self.connection.cursor() as cursor:
            cursor.execute("""
            UPDATE stock_basic SET last_update=CURDATE() WHERE code=%s
            """, (code,))
            self.connection.commit()
    
    def save_screen_result(self, result, strategy_name="default"):
        """保存选股结果到数据库"""
        if not result:
            return
        
        today = datetime.now().date()
        data = []
        for code, name, price in result:
            data.append((today, code, name, price, strategy_name))
        
        with self.connection.cursor() as cursor:
            cursor.executemany("""
            INSERT IGNORE INTO stock_screen_result
            (screen_date, code, name, close_price, strategy_name)
            VALUES (%s, %s, %s, %s, %s)
            """, data)
            self.connection.commit()
        logger.info(f"✅ 选股结果已保存到数据库，共 {len(result)} 条")
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info("✅ 数据库连接已关闭")