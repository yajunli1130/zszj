from .utils import logger
from .data_fetcher import fetch_today_market

def run_hot_analysis():
    """运行今日市场热点分析"""
    print("\n" + "="*70)
    print("🔥 今日市场热点监控")
    print("="*70)
    
    df_all = fetch_today_market()
    
    # 涨幅榜TOP10
    print("\n📈 涨幅榜 TOP 10:")
    top_gainers = df_all.nlargest(10, 'change_pct')[['code', 'code_name', 'close', 'change_pct']]
    for _, row in top_gainers.iterrows():
        print(f"  {row['code']} {row['code_name']:10}  现价:{row['close']:.2f}  涨幅:{row['change_pct']:.2f}%")
    
    # 涨停股分析
    print("\n🚀 涨停股分析:")
    limit_up = df_all[df_all['change_pct'] >= 9.9]
    print(f"  今日涨停股数量: {len(limit_up)} 只")
    
    # 成交量榜TOP10
    print("\n💰 成交量榜 TOP 10:")
    top_volume = df_all.nlargest(10, 'volume')[['code', 'code_name', 'volume', 'change_pct']]
    for _, row in top_volume.iterrows():
        vol_亿 = row['volume'] / 100000000
        print(f"  {row['code']} {row['code_name']:10}  成交量:{vol_亿:.2f}亿  涨幅:{row['change_pct']:.2f}%")