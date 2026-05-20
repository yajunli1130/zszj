import pandas as pd
from .config import INDICATOR_CONFIG

def calculate_all_indicators(df):
    """计算所有技术指标"""
    cfg = INDICATOR_CONFIG
    
    # 均线系统
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    
    # MACD
    ema_fast = df['close'].ewm(span=cfg['fast_period'], adjust=False).mean()
    ema_slow = df['close'].ewm(span=cfg['slow_period'], adjust=False).mean()
    df['dif'] = ema_fast - ema_slow
    df['dea'] = df['dif'].ewm(span=cfg['signal_period'], adjust=False).mean()
    df['macd'] = 2 * (df['dif'] - df['dea'])
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    avg_gain = gain.rolling(cfg['rsi_period']).mean()
    avg_loss = loss.rolling(cfg['rsi_period']).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # KDJ
    low_list = df['low'].rolling(cfg['kdj_n'], min_periods=1).min()
    high_list = df['high'].rolling(cfg['kdj_n'], min_periods=1).max()
    rsv = (df['close'] - low_list) / (high_list - low_list) * 100
    df['k'] = rsv.ewm(com=cfg['kdj_m1']-1, adjust=False).mean()
    df['d'] = df['k'].ewm(com=cfg['kdj_m2']-1, adjust=False).mean()
    
    # 成交量均线
    df['ma5_vol'] = df['volume'].rolling(5).mean()
    
    # 布林带
    df['boll_mid'] = df['close'].rolling(cfg['boll_period']).mean()
    
    return df