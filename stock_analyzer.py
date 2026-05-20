import baostock as bs
import pandas as pd
import time
from collections import Counter

# ==================================================
# 🎛️ 全局配置区（所有参数都在这里调整，不用改下面的代码）
# ==================================================
# -------------------------- MACD指标参数 --------------------------
# MACD是最常用的趋势指标，标准参数12/26/9，短线交易可改为6/12/3
FAST_PERIOD = 12       # 快速EMA均线周期（默认12）
SLOW_PERIOD = 26       # 慢速EMA均线周期（默认26）
SIGNAL_PERIOD = 9      # DEA信号线周期（默认9）

# -------------------------- RSI相对强弱指标参数 --------------------------
# RSI用于判断股票超买超卖，0-30超卖，70-100超买
RSI_PERIOD = 14        # RSI计算周期（默认14）
RSI_LOWER = 30         # RSI下限（低于此值为超卖）
RSI_UPPER = 50         # RSI上限（高于此值避免追高）

# -------------------------- KDJ随机指标参数 --------------------------
# KDJ用于捕捉短期买卖点，金叉买入，死叉卖出
KDJ_N = 9              # KDJ周期（默认9）
KDJ_M1 = 3             # K线平滑系数（默认3）
KDJ_M2 = 3             # D线平滑系数（默认3）

# -------------------------- 布林带指标参数 --------------------------
# 布林带用于判断股价波动区间，中轨以上为强势，中轨以下为弱势
BOLL_PERIOD = 20       # 布林带中轨周期（默认20）
BOLL_STD = 2           # 布林带上下轨标准差倍数（默认2）

# -------------------------- 量能指标参数 --------------------------
# 成交量放大确认资金进场，倍数越大信号越强
VOLUME_MULTIPLE = 1.2  # 成交量放大倍数（默认1.2倍，即今日成交量>5日均量*1.2）

# -------------------------- 股价过滤参数 --------------------------
# 只筛选股价在指定区间的股票，避免高价股
MIN_PRICE = 0          # 最低股价（默认0元，不限制）
MAX_PRICE = 30         # 最高股价（默认30元，只看30元以下）

# -------------------------- 网络请求参数 --------------------------
# 控制请求频率，防止被服务器封IP
REQUEST_DELAY = 0.2    # 每只股票请求间隔（秒），不要低于0.1

# -------------------------- 选股开关 --------------------------
# 可以单独开启/关闭任意一个选股条件，True=开启，False=关闭
USE_MA = True          # 均线多头排列（MA5>MA10>MA20>MA60）
USE_MACD = True        # MACD金叉（DIF上穿DEA+MACD柱由负变正）
USE_RSI = True         # RSI区间过滤（30<RSI<50，相对低位）
USE_KDJ = True         # KDJ金叉（K线上穿D线）
USE_VOLUME = True      # 成交量放大过滤
USE_BOLL = True        # 布林带中轨以上（股价站在中轨之上）
USE_PRICE = True       # 股价区间过滤（0-30元）
# ==================================================

def login_baostock():
    """登录baostock（无需账号密码，免费使用）"""
    lg = bs.login()
    if lg.error_code != '0':
        print(f"❌ 登录失败：{lg.error_msg}")
        return False
    print("✅ baostock登录成功")
    return True

def get_stock_list():
    """获取沪深A股股票列表（自动过滤垃圾股）"""
    print("📥 正在获取股票列表...")
    
    rs = bs.query_stock_basic()
    df = rs.get_data()
    
    # 基础过滤条件（不建议修改）
    df = df[df['type'] == '1']  # 只保留A股
    df = df[df['status'] == '1']  # 只保留上市状态的股票
    # 修复：转义正则特殊字符*，正确过滤*ST股票
    df = df[~df['code_name'].str.contains(r'ST|退|\*ST')]  # 过滤ST、*ST、退市股
    df = df[df['code'].str.startswith(('sh.', 'sz.'))]  # 只保留沪深A股
    df = df[~df['code'].str.startswith('sz.300')]  # 过滤创业板
    df = df[~df['code'].str.startswith('sh.688')]  # 过滤科创板
    df = df[~df['code'].str.startswith('bj.')]  # 过滤北交所
    
    df = df[['code', 'code_name']]
    return df.reset_index(drop=True)

def calculate_indicators(df):
    """计算所有技术指标（无需修改）"""
    # 转换为数值类型
    df['close'] = pd.to_numeric(df['close'])
    df['open'] = pd.to_numeric(df['open'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['volume'] = pd.to_numeric(df['volume'])
    
    # 1. 均线系统（MA5/MA10/MA20/MA60）
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    
    # 2. MACD指标
    ema_fast = df['close'].ewm(span=FAST_PERIOD, adjust=False).mean()
    ema_slow = df['close'].ewm(span=SLOW_PERIOD, adjust=False).mean()
    df['dif'] = ema_fast - ema_slow
    df['dea'] = df['dif'].ewm(span=SIGNAL_PERIOD, adjust=False).mean()
    df['macd'] = 2 * (df['dif'] - df['dea'])
    
    # 3. RSI相对强弱指标
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    avg_gain = gain.rolling(RSI_PERIOD).mean()
    avg_loss = loss.rolling(RSI_PERIOD).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 4. KDJ随机指标
    low_list = df['low'].rolling(KDJ_N, min_periods=1).min()
    high_list = df['high'].rolling(KDJ_N, min_periods=1).max()
    rsv = (df['close'] - low_list) / (high_list - low_list) * 100
    df['k'] = rsv.ewm(com=KDJ_M1-1, adjust=False).mean()
    df['d'] = df['k'].ewm(com=KDJ_M2-1, adjust=False).mean()
    df['j'] = 3 * df['k'] - 2 * df['d']
    
    # 5. 成交量均线
    df['ma5_vol'] = df['volume'].rolling(5).mean()
    
    # 6. 布林带指标
    df['boll_mid'] = df['close'].rolling(BOLL_PERIOD).mean()
    df['boll_std'] = df['close'].rolling(BOLL_PERIOD).std()
    df['boll_upper'] = df['boll_mid'] + BOLL_STD * df['boll_std']
    df['boll_lower'] = df['boll_mid'] - BOLL_STD * df['boll_std']
    
    return df

def check_conditions(df):
    """检查所有选股条件（根据配置自动判断）"""
    if len(df) < 60:  # 数据不足60个交易日，无法计算所有指标
        return False
    
    df = calculate_indicators(df)
    
    # 获取最新两天数据
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 条件1：均线多头排列（大趋势向上）
    cond_ma = True
    if USE_MA:
        cond_ma = (latest['ma5'] > latest['ma10']) and \
                  (latest['ma10'] > latest['ma20']) and \
                  (latest['ma20'] > latest['ma60'])
    
    # 条件2：MACD金叉（趋势转折信号）
    cond_macd = True
    if USE_MACD:
        cond_macd = (prev['dif'] < prev['dea']) and \
                    (latest['dif'] > latest['dea']) and \
                    (latest['macd'] > 0)
    
    # 条件3：RSI在合理区间（避免追高，只买相对低位）
    cond_rsi = True
    if USE_RSI:
        cond_rsi = (latest['rsi'] > RSI_LOWER) and (latest['rsi'] < RSI_UPPER)
    
    # 条件4：KDJ金叉（短期买点信号）
    cond_kdj = True
    if USE_KDJ:
        cond_kdj = (prev['k'] < prev['d']) and (latest['k'] > latest['d'])
    
    # 条件5：成交量放大（确认有资金进场）
    cond_volume = True
    if USE_VOLUME:
        cond_volume = latest['volume'] > latest['ma5_vol'] * VOLUME_MULTIPLE
    
    # 条件6：股价站在布林带中轨之上（强势股特征）
    cond_boll = True
    if USE_BOLL:
        cond_boll = latest['close'] > latest['boll_mid']
    
    # 条件7：股价在指定区间内
    cond_price = True
    if USE_PRICE:
        cond_price = (latest['close'] > MIN_PRICE) and (latest['close'] < MAX_PRICE)
    
    # 所有开启的条件必须同时满足
    return cond_ma and cond_macd and cond_rsi and cond_kdj and cond_volume and cond_boll and cond_price

def screen_stocks():
    """多指标综合选股主函数"""
    print("\n" + "=" * 70)
    print("📊 多指标综合选股系统（已过滤创业板/科创板/30元以上高价股）")
    print("=" * 70)
    
    stock_list = get_stock_list()
    total = len(stock_list)
    print(f"📊 待筛选股票总数：{total} 只")
    print(f"💰 股价过滤范围：{MIN_PRICE}元 - {MAX_PRICE}元")
    print("⏳ 开始筛选，请耐心等待...\n")
    
    result = []
    count = 0
    
    for index, row in stock_list.iterrows():
        code = row['code']
        name = row['code_name']
        
        try:
            # 获取近60个交易日的前复权日线数据
            rs = bs.query_history_k_data_plus(
                code,
                "date,open,high,low,close,volume",
                start_date="",
                end_date="",
                frequency="d",
                adjustflag="2"  # 2=前复权，必须用前复权数据计算指标
            )
            
            df = rs.get_data()
            
            if check_conditions(df):
                latest_price = round(pd.to_numeric(df['close'].iloc[-1]), 2)
                result.append([code, name, latest_price])
                print(f"✅ 符合条件：{code} | {name} | 现价：{latest_price}元")
        
        except Exception as e:
            pass
        
        count += 1
        if count % 10 == 0:
            print(f"\n⏳ 已完成 {count}/{total} 只股票筛选...")
        
        time.sleep(REQUEST_DELAY)
    
    # 输出最终选股结果
    print("\n" + "=" * 70)
    print("🏆 今日多指标共振精选股票列表")
    print("=" * 70)
    
    if result:
        # 按股价从低到高排序
        result.sort(key=lambda x: x[2])
        for stock in result:
            print(f"🔹 {stock[0]}  {stock[1]:10}  现价：{stock[2]}元")
        
        # 保存到Excel文件
        df_result = pd.DataFrame(result, columns=['股票代码', '股票名称', '最新股价(元)'])
        df_result.to_excel('多指标综合选股结果_30元以下.xlsx', index=False)
        print(f"\n📁 选股结果已保存到：多指标综合选股结果_30元以下.xlsx")
    else:
        print("❌ 今日无符合所有条件的股票")
    
    return result

def get_hot_analysis():
    """今日市场热点监控"""
    print("\n" + "=" * 70)
    print("🔥 今日市场热点监控")
    print("=" * 70)
    
    # 获取今日所有股票行情
    print("📥 正在获取今日行情数据...")
    rs = bs.query_all_stock(day="")
    df_all = rs.get_data()
    
    # 过滤股票（和选股池保持一致）
    df_all = df_all[df_all['code'].str.startswith(('sh.', 'sz.'))]
    df_all = df_all[~df_all['code'].str.startswith('sz.300')]
    df_all = df_all[~df_all['code'].str.startswith('sh.688')]
    df_all = df_all[~df_all['code'].str.startswith('bj.')]
    
    # 转换数值类型
    df_all['close'] = pd.to_numeric(df_all['close'])
    df_all['preclose'] = pd.to_numeric(df_all['preclose'])
    df_all['volume'] = pd.to_numeric(df_all['volume'])
    
    # 计算涨跌幅
    df_all['change_pct'] = (df_all['close'] - df_all['preclose']) / df_all['preclose'] * 100
    
    # 1. 涨幅榜前10
    print("\n📈 涨幅榜 TOP 10:")
    top_gainers = df_all.nlargest(10, 'change_pct')[['code', 'code_name', 'close', 'change_pct']]
    for _, row in top_gainers.iterrows():
        print(f"  {row['code']} {row['code_name']:10}  现价:{row['close']:.2f}  涨幅:{row['change_pct']:.2f}%")
    
    # 2. 涨停股分析
    print("\n🚀 涨停股分析:")
    limit_up = df_all[df_all['change_pct'] >= 9.9]
    print(f"  今日涨停股数量：{len(limit_up)} 只")
    
    # 3. 成交量榜前10
    print("\n💰 成交量榜 TOP 10:")
    top_volume = df_all.nlargest(10, 'volume')[['code', 'code_name', 'volume', 'change_pct']]
    for _, row in top_volume.iterrows():
        vol_亿 = row['volume'] / 100000000
        print(f"  {row['code']} {row['code_name']:10}  成交量:{vol_亿:.2f}亿  涨幅:{row['change_pct']:.2f}%")

if __name__ == '__main__':
    if not login_baostock():
        exit()
    
    # 运行多指标选股
    screen_stocks()
    
    # 运行热点监控
    get_hot_analysis()
    
    bs.logout()
    print("\n✅ 程序运行结束")