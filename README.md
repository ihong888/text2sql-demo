# text2sql-demo

用自然语言查询 MySQL 数据库：输入一句中文问题，AI 自动生成 SQL 并返回查询结果。

## 背景

作者有 6 年企业软件实施经验（政企监管 / 建筑检测 / 医疗信息化），正转型 AI 应用落地方向。本项目的目标是练熟"大模型 + 数据库"的落地链路：Prompt 工程、工具调用、SQL 生成与执行、错误自修复。

## 功能

- 命令行交互，输入中文问题直接查库
- 自动把表结构注入 Prompt，让模型只返回可执行 SQL
- SQL 执行失败时自动带错误信息让模型修正重试
- 支持多表 JOIN、聚合查询

## 演示效果

- 问：广州有哪些客户？ → SELECT * FROM customers WHERE city = '广州'
- 问：订单金额最高的 5 笔？ → ORDER BY amount DESC LIMIT 5
- 问：制造业客户一共下了多少单、总金额？ → JOIN + COUNT + SUM 自动生成

## 快速开始

1. 安装依赖：pip install pymysql openai
2. 设置环境变量：DEEPSEEK_API_KEY=你的key（模型 deepseek-chat）
3. 初始化数据：python init_db.py（建库建表插 20 条假数据）
4. 运行：python text2sql.py
5. 输入 exit 退出

## 技术栈

Python 3 · MySQL 8 · DeepSeek API（deepseek-chat）
