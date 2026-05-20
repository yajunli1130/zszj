import baostock as bs
import pandas as pd
import time
from datetime import datetime, timedelta
from .config import FILTER_CONFIG
from .utils import logger

def login_baostock():
    """登录baostock（带重试）"""
    for attempt in range(3):
        try:
            lg = bs.login()
            if lg.error_code == '0':
                logger.info("baostock登录成功")
                return True
            logger.warning(f"登录失败，重试 {attempt+1}/3: {lg.error_msg}")
        except Exception as e:
            logger.warning(f"登录异常，重试 {attempt+1}/3: {str(e)}")
        time.sleep(2)
    logger.error("baostock登录失败")
    return False

def logout_baostock():
    """登出baostock"""
    bs.logout()
    logger.info("baostock已登出")

def get_stock_list():
    """获取过滤后的股票列表"""
    logger.info("正在从baostock获取股票列表...")
    rs = bs.query_stock_basic()
    df = rs.get_data()
    
    # 基础过滤
    df = df[df['type'] == '1']  # A股
    df = df[df['status'] == '1']  # 上市状态
    df = df[~df['code_name'].str.contains(r'ST|退|\*ST')]  # 过滤ST/退市
    df = df[df['code'].str.startswith(('sh.', 'sz.'))]  # 沪深A股
    df = df[~df['code'].str.startswith('sz.300')]  # 过滤创业板
    df = df[~df['code'].str.startswith('sh.688')]  # 过滤科创板
    df = df[~df['code'].str.startswith('bj.')]  # 过滤北交所
    
    return list(zip(df['code'], df['code_name']))

def fetch_daily_data(code, start_date, end_date):
    """获取单只股票的日线数据"""
    try:
        rs = bs.query_history_k_data_plus(
            code,
            "date,open,high,low,close,preclose,volume,amount,turn",  # 新增字段
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="2"  # 前复权
        )
        
        df = rs.get_data()
        if df.empty:
            return df
        
        # 转换数值类型
        numeric_cols = ['open', 'high', 'low', 'close', 'preclose', 'volume', 'amount', 'turn']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col])
        
        return df
    except Exception as e:
        logger.error(f"获取 {code} 数据失败: {str(e)}")
        return pd.DataFrame()

def fetch_today_market():
    """获取今日全市场行情"""
    logger.info("正在获取今日市场行情数据...")
    rs = bs.query_all_stock(day="")
    df = rs.get_data()
    
    # 过滤股票
    df = df[df['code'].str.startswith(('sh.', 'sz.'))]
    df = df[~df['code'].str.startswith('sz.300')]
    df = df[~df['code'].str.startswith('sh.688')]
    df = df[~df['code'].str.startswith('bj.')]
    
    # 转换数值类型
    for col in ['close', 'preclose', 'volume']:
        df[col] = pd.to_numeric(df[col])
    
    # 计算涨跌幅
    df['change_pct'] = (df['close'] - df['preclose']) / df['preclose'] * 100
    
    return df