import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def get_bool_env(key, default=True):
    value = os.getenv(key, str(default)).lower()
    return value in ('true', '1', 'yes')

# 数据库配置
DB_CONFIG = {
    "host": os.getenv("DB_HOST", ""),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "stock_user"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "stock_db"),

}

# 指标参数
INDICATOR_CONFIG = {
    "fast_period": int(os.getenv("FAST_PERIOD", 12)),
    "slow_period": int(os.getenv("SLOW_PERIOD", 26)),
    "signal_period": int(os.getenv("SIGNAL_PERIOD", 9)),
    "rsi_period": int(os.getenv("RSI_PERIOD", 14)),
    "rsi_lower": int(os.getenv("RSI_LOWER", 30)),
    "rsi_upper": int(os.getenv("RSI_UPPER", 50)),
    "kdj_n": int(os.getenv("KDJ_N", 9)),
    "kdj_m1": int(os.getenv("KDJ_M1", 3)),
    "kdj_m2": int(os.getenv("KDJ_M2", 3)),
    "boll_period": int(os.getenv("BOLL_PERIOD", 20)),
    "boll_std": int(os.getenv("BOLL_STD", 2)),
    "volume_multiple": float(os.getenv("VOLUME_MULTIPLE", 1.2))
}

# 过滤参数
FILTER_CONFIG = {
    "min_price": float(os.getenv("MIN_PRICE", 0)),
    "max_price": float(os.getenv("MAX_PRICE", 30)),
    "request_delay": float(os.getenv("REQUEST_DELAY", 0.1))
}

# 选股开关
SCREENER_SWITCH = {
    "use_ma": get_bool_env("USE_MA", True),
    "use_macd": get_bool_env("USE_MACD", True),
    "use_rsi": get_bool_env("USE_RSI", True),
    "use_kdj": get_bool_env("USE_KDJ", True),
    "use_volume": get_bool_env("USE_VOLUME", True),
    "use_boll": get_bool_env("USE_BOLL", True),
    "use_price": get_bool_env("USE_PRICE", True)
}