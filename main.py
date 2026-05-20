from stock_selector.database import StockDB
from stock_selector.data_fetcher import login_baostock, logout_baostock, get_stock_list
from stock_selector.screener import update_and_screen
from stock_selector.hot_analysis import run_hot_analysis
from stock_selector.utils import logger

def main():
    logger.info("="*70)
    logger.info("📊 多指标综合选股系统（模块化版）启动")
    logger.info("="*70)
    
    # 初始化数据库
    try:
        db = StockDB()
    except Exception as e:
        logger.error("数据库初始化失败，程序退出")
        return
    
    # 登录baostock
    if not login_baostock():
        db.close()
        return
    
    try:
        # 更新股票列表
        stock_list = get_stock_list()
        db.update_stock_list(stock_list)
        
        # 执行选股
        update_and_screen(db)
        
        # 运行热点分析
        run_hot_analysis()
    
    except Exception as e:
        logger.error(f"程序运行异常: {str(e)}", exc_info=True)
    finally:
        logout_baostock()
        db.close()
        logger.info("程序运行结束")

if __name__ == '__main__':
    main()