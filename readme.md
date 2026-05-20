1. 安装依赖
bash
运行
# 激活虚拟环境
source venv/bin/activate

# 安装所有依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
2. 配置环境变量
bash
运行
# 复制环境变量示例文件
cp .env.example .env

# 编辑.env文件，修改数据库密码和其他参数
nano .env
3. 运行程序
bash
运行
python main.py
4. 更新定时任务
bash
运行
crontab -e