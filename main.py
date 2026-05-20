import time
import datetime
import logging

# ====================== 【你自己改这里】 ======================
# 券商账号
ACCOUNT = "你的中山证券资金账号"
PASSWORD = "你的交易密码"
# 股票
TARGET_STOCK = "600000"
BUY_AMOUNT = 100

# 止盈止损
STOP_LOSS_RATE = 0.02
PROFIT_RATE = 0.01

# ========== 动态大单：按 价格×手数=金额 判断 ==========
SINGLE_AMT_THRESHOLD = 500000   # 单笔≥50万元算大单
SINGLE_HAND_THRESHOLD = 200     # 单笔≥200手（防低价垃圾单）
TOTAL_AMT_THRESHOLD = 2000000   # 5分钟累计≥200万元主动买入
MONITOR_INTERVAL = 2              # 盘口刷新间隔(秒)
# =====================================================================

# 日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='trading_log.log',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

# ---------------- 中山证券接口（有实盘就用真实，没有先模拟跑逻辑）----------------
# 实盘时打开下面这句：
# from zsht import ZSHTClient
# client = ZSHTClient()

class MockStockApi:
    def __init__(self):
        pass
    def login(self, acc, pwd):
        logger.info("✅ 中山证券模拟登录成功")
        return True

    def get_realtime_trades(self, code):
        """
        返回最近逐笔成交：[{price, hand, amt, is_buy}, ...]
        实盘这里换成券商 Level2 逐笔成交接口
        """
        # 模拟：当前股价 25 元，出现 600 手主动买单
        price = 25.0
        hand = 600
        amt = price * hand * 100  # 金额
        return [
            {"price": price, "hand": hand, "amt": amt, "is_buy": True},
        ]

    def get_price(self, code):
        return 25.0

    def buy_market(self, code, vol):
        logger.info(f"✅ 触发大笔买入+时间窗口 市价买入 {code} {vol}手")
        return True

    def get_position(self, code):
        return 100

    def get_cost_price(self, code):
        return 24.8

    def sell_market(self, code, vol):
        logger.info(f"✅ 早盘强制清仓 卖出 {code} {vol}手")
        return True

client = MockStockApi()

# ====================== 时间判断（不变） ======================
def get_trade_time_status():
    now = datetime.datetime.now()
    current_time = now.time()
    if now.weekday() >= 5:
        return 0

    # 今日尾盘
    if datetime.time(14,30,0) <= current_time < datetime.time(14,40,0):
        return 1
    elif datetime.time(14,40,0) <= current_time < datetime.time(14,45,0):
        return 2
    elif current_time >= datetime.time(14,50,0):
        return 3

    # 次日早盘卖出
    if datetime.time(9,30,0) <= current_time < datetime.time(9,35,0):
        return 4
    elif datetime.time(9,35,0) <= current_time < datetime.time(9,40,0):
        return 5
    elif datetime.time(9,40,0) <= current_time < datetime.time(10,0,0):
        return 6
    return 0

# ====================== 核心：按 金额+手数 双条件判断大笔买入 ======================
def check_big_buy():
    """
    检查最近成交是否出现：
    1. 单笔金额≥SINGLE_AMT_THRESHOLD 且 手数≥SINGLE_HAND_THRESHOLD
    2. 5分钟内主动买入累计金额≥TOTAL_AMT_THRESHOLD
    """
    trades = client.get_realtime_trades(TARGET_STOCK)
    now = datetime.datetime.now()
    total_amt = 0
    has_single_big = False

    for t in trades:
        # 只看主动买单
        if not t["is_buy"]:
            continue

        # 时间过滤：只看最近5分钟
        # （模拟版省略时间，实盘要加）
        # 单笔条件
        if t["amt"] >= SINGLE_AMT_THRESHOLD and t["hand"] >= SINGLE_HAND_THRESHOLD:
            has_single_big = True
            logger.info(f"💥 单笔大单：{t['price']}元 {t['hand']}手 金额{t['amt']/10000:.1f}万")

        total_amt += t["amt"]

    logger.info(f"📊 近5分钟主动买入累计：{total_amt/10000:.1f}万")

    # 满足任一条件即可（你也可以改成 and 更严）
    return has_single_big or (total_amt >= TOTAL_AMT_THRESHOLD)

# ====================== 买卖函数 ======================
def buy_stock():
    try:
        price = client.get_price(TARGET_STOCK)
        # client.buy_market(TARGET_STOCK, BUY_AMOUNT)
        logger.info(f"📈 跟买成功 | 股价{price}")
        return True
    except Exception as e:
        logger.error(f"买入异常：{e}")
        return False

def sell_stock():
    try:
        pos = client.get_position(TARGET_STOCK)
        if pos <= 0:
            logger.info("无持仓无需卖出")
            return True
        now_price = client.get_price(TARGET_STOCK)
        cost = client.get_cost_price(TARGET_STOCK)
        rate = (now_price - cost) / cost

        if rate >= PROFIT_RATE or rate <= -STOP_LOSS_RATE:
            # client.sell_market(TARGET_STOCK, pos)
            logger.info(f"📉 清仓卖出 盈亏比例：{rate:.2%}")
        return True
    except Exception as e:
        logger.error(f"卖出异常：{e}")
        return False

# ====================== 主逻辑 ======================
def main():
    print("🚀 启动：尾盘定时 + 金额+手数双维度大单跟买")
    client.login(ACCOUNT, PASSWORD)

    bought = False
    sold = False

    while True:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = get_trade_time_status()

        if status == 1:
            print(f"[{now_str}] 🔍 14:30-14:40 观察盘口，监控大单...")
            check_big_buy()

        elif status == 2 and not bought:
            print(f"[{now_str}] ⏰ 14:40-14:45 最佳买点，校验主力大单...")
            if check_big_buy():
                print(f"[{now_str}] ✅ 检测到大笔主动买入（金额+手数达标），执行跟买！")
                buy_stock()
                bought = True
            else:
                print(f"[{now_str}] ❌ 无达标大笔买单，放弃今日买入")

        elif status == 3:
            print(f"[{now_str}] ⛔ 14:50过后，禁止任何买入")

        # 次日卖出
        if status in [4,5,6] and not sold:
            print(f"[{now_str}] 🔔 早盘卖出窗口，强制清仓")
            sell_stock()
            sold = True
            if status == 6:
                print(f"[{now_str}] ✅ 10点前已清仓，本轮结束")
                break

        time.sleep(MONITOR_INTERVAL)

if __name__ == "__main__":
    main()