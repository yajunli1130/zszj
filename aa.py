import baostock as bs
import pandas as pd
import time

# ====================== 配置区 ======================
# MACD标准参数
FAST_PERIOD = 12
SLOW_PERIOD = 26
SIGNAL_PERIOD = 9
# 请求间隔（秒），防止被封
REQUEST_DELAY = 0.2
# ====================================================

def login_baostock():
    """登录baostock（无需账号密码）"""
    lg = bs.login()
    if lg.error_code != '0':
        print(f"❌ 登录失败：{lg.error_msg}")
        return False
    print("✅ baostock登录成功")
    return True

def get_stock_list():
    """获取沪深A股股票列表（自动过滤ST、退市、创业板）"""
    print("📥 正在获取股票列表...")
    
    # 获取所有上市股票
    rs = bs.query_stock_basic()
    df = rs.get_data()
    
    # 过滤条件：
    # 1. 只保留A股（type=1）
    # 2. 只保留上市状态（status=1）
    # 3. 过滤ST、*ST、退市股
    # 4. 只保留沪深A股（代码以sh.或sz.开头）
    # 5. 过滤创业板（代码以sz.300开头）
    df = df[df['type'] == '1']
    df = df[df['status'] == '1']
    df = df[~df['code_name'].str.contains('ST|退')]
    df = df[df['code'].str.startswith(('sh.', 'sz.'))]
    df = df[~df['code'].str.startswith('sz.300')]  # 新增：过滤创业板
    
    # 只保留需要的列
    df = df[['code', 'code_name']]
    return df.reset_index(drop=True)

def calculate_macd(close, fast=12, slow=26, signal=9):
    """纯Python计算MACD指标"""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd = 2 * (dif - dea)
    return dif, dea, macd

def check_gold_cross(stock_code):
    """检查单只股票是否出现MACD金叉"""
    try:
        # 获取近60个交易日的前复权日线数据
        rs = bs.query_history_k_data_plus(
            stock_code,
            "date,close,volume",
            start_date="",
            end_date="",
            frequency="d",
            adjustflag="2"  # 2=前复权，关键！
        )
        
        df = rs.get_data()
        if len(df) < 30:
            return False
        
        # 转换为数值类型
        df['close'] = pd.to_numeric(df['close'])
        df['volume'] = pd.to_numeric(df['volume'])
        
        # 计算MACD
        dif, dea, macd = calculate_macd(df['close'])
        
        # 严格金叉判断（避免假信号）
        # 前一天DIF < DEA，今天DIF > DEA，且今天MACD柱为正
        cond1 = dif.iloc[-2] < dea.iloc[-2]
        cond2 = dif.iloc[-1] > dea.iloc[-1]
        cond3 = macd.iloc[-1] > 0
        
        # 可选：添加成交量放大过滤（今日成交量>5日均量的1.2倍）
        # df['ma5_vol'] = df['volume'].rolling(5).mean()
        # cond4 = df['volume'].iloc[-1] > df['ma5_vol'].iloc[-1] * 1.2
        
        return cond1 and cond2 and cond3
    
    except Exception as e:
        return False

def screen_stocks():
    """MACD金叉选股主函数"""
    print("=" * 60)
    print("📈 baostock 版 MACD 金叉自动选股软件（已过滤创业板）")
    print("=" * 60)
    
    # 登录
    if not login_baostock():
        return
    
    # 获取股票列表
    stock_list = get_stock_list()
    total = len(stock_list)
    print(f"📊 待筛选股票总数：{total} 只（已过滤创业板）")
    print("⏳ 开始筛选，请耐心等待...\n")
    
    result = []
    count = 0
    
    # 遍历选股
    for index, row in stock_list.iterrows():
        code = row['code']
        name = row['code_name']
        
        if check_gold_cross(code):
            result.append([code, name])
            print(f"✅ 发现金叉：{code} | {name}")
        
        count += 1
        # 每100只显示进度
        if count % 10 == 0:
            print(f"\n⏳ 已完成 {count}/{total} 只股票筛选...")
        
        # 控制请求频率
        time.sleep(REQUEST_DELAY)
    
    # 输出最终结果
    print("\n" + "=" * 60)
    print("🏆 今日 MACD 金叉 精选股票列表（主板+中小板）")
    print("=" * 60)
    
    if result:
        for stock in result:
            print(f"🔹 {stock[0]}  {stock[1]}")
        
        # 保存到Excel
        df_result = pd.DataFrame(result, columns=['股票代码', '股票名称'])
        df_result.to_excel('MACD金叉选股结果_主板中小板.xlsx', index=False)
        print(f"\n📁 结果已保存到：MACD金叉选股结果_主板中小板.xlsx")
    else:
        print("❌ 今日无符合条件的 MACD 金叉股票")
    
    # 登出
    bs.logout()
    print("\n✅ 程序运行结束")

if __name__ == '__main__':
    screen_stocks()