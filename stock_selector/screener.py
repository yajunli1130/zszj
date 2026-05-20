import time
import pandas as pd
from datetime import datetime, timedelta
from .config import INDICATOR_CONFIG, FILTER_CONFIG, SCREENER_SWITCH
from .utils import logger
from .indicators import calculate_all_indicators
from .data_fetcher import fetch_daily_data

def check_conditions(df):
    """检查所有选股条件"""
    if len(df) < 60:
        return False
    
    df = calculate_all_indicators(df)
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    cfg = INDICATOR_CONFIG
    switch = SCREENER_SWITCH
    filter_cfg = FILTER_CONFIG
    
    # 条件判断
    cond_ma = (latest['ma5'] > latest['ma10']) and \
              (latest['ma10'] > latest['ma20']) and \
              (latest['ma20'] > latest['ma60']) if switch['use_ma'] else True
    
    cond_macd = (prev['dif'] < prev['dea']) and \
                (latest['dif'] > latest['dea']) and \
                (latest['macd'] > 0) if switch['use_macd'] else True
    
    cond_rsi = (latest['rsi'] > cfg['rsi_lower']) and \
               (latest['rsi'] < cfg['rsi_upper']) if switch['use_rsi'] else True
    
    cond_kdj = (prev['k'] < prev['d']) and \
               (latest['k'] > latest['d']) if switch['use_kdj'] else True
    
    cond_volume = latest['volume'] > latest['ma5_vol'] * cfg['volume_multiple'] if switch['use_volume'] else True
    
    cond_boll = latest['close'] > latest['boll_mid'] if switch['use_boll'] else True
    
    cond_price = (latest['close'] > filter_cfg['min_price']) and \
                 (latest['close'] < filter_cfg['max_price']) if switch['use_price'] else True
    
    return all([cond_ma, cond_macd, cond_rsi, cond_kdj, cond_volume, cond_boll, cond_price])

def update_and_screen(db):
    """更新数据并执行选股"""
    stock_list = db.get_stock_list()
    total = len(stock_list)
    result = []
    count = 0
    
    logger.info(f"开始处理 {total} 只股票...")
    start_time = time.time()
    
    for stock in stock_list:
        code = stock['code']
        name = stock['name']
        
        try:
            # 增量更新数据
            last_date = db.get_last_trade_date(code)
            today = datetime.now().date()
            
            if last_date != today:
                start_date = (last_date + timedelta(days=1)).strftime('%Y-%m-%d') if last_date else \
                            (today - timedelta(days=120)).strftime('%Y-%m-%d')
                end_date = today.strftime('%Y-%m-%d')
                
                if start_date <= end_date:
                    df = fetch_daily_data(code, start_date, end_date)
                    if not df.empty:
                        db.insert_daily_data(code, df)
                db.update_last_update(code)
            
            # 从数据库读取数据并选股
            df = db.get_daily_data(code, days=60)
            if check_conditions(df):
                latest_price = round(df['close'].iloc[-1], 2)
                result.append([code, name, latest_price])
                logger.info(f"符合条件: {code} | {name} | 现价: {latest_price}元")
        
        except Exception as e:
            logger.error(f"处理 {code} 异常: {str(e)}")
        
        count += 1
        if count % 100 == 0:
            logger.info(f"已完成 {count}/{total} 只股票处理")
        
        time.sleep(FILTER_CONFIG['request_delay'])
    
    end_time = time.time()
    logger.info(f"选股完成，耗时: {round(end_time - start_time, 2)} 秒")
    
    # 保存结果
    if result:
        result.sort(key=lambda x: x[2])
        today_str = datetime.now().strftime('%Y%m%d')
        df_result = pd.DataFrame(result, columns=['股票代码', '股票名称', '最新股价(元)'])
        df_result.to_excel(f'选股结果_{today_str}.xlsx', index=False)
        logger.info(f"结果已保存到: 选股结果_{today_str}.xlsx")
        
        # 打印结果
        print("\n" + "="*70)
        print("🏆 今日多指标共振精选股票列表")
        print("="*70)
        for stock in result:
            print(f"🔹 {stock[0]}  {stock[1]:10}  现价: {stock[2]}元")
    else:
        logger.info("今日无符合所有条件的股票")
    db.save_screen_result(result)

    return result