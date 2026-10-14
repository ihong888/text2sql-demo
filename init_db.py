# -*- coding: utf-8 -*-
"""
第 1 步：初始化 Text-to-SQL 练习库 company_demo

做什么：
1. 连接本机 MySQL（还不选库，因为库可能还不存在）
2. 创建数据库 company_demo（如果已存在则先删再建，方便反复练习）
3. 创建 customers、orders 两张表
4. 各插入 20 条合理的假数据
5. 查询条数，确认成功

运行方式（在本文件所在目录打开终端）：
    python init_db.py
"""

import pymysql

# ---------- 连接参数（本机练手用，正式项目请改用环境变量，不要写死密码）----------
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "abc123456"
DB_NAME = "company_demo"


def get_connection(database=None):
    """创建并返回一个 MySQL 连接。database=None 表示先不指定库。"""
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=database,  # None 时连上服务器即可，用来 CREATE DATABASE
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,  # 查询结果用字典，方便按列名取值
    )


def create_database():
    """创建练习库。IF EXISTS 删掉旧库，保证脚本可重复执行。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # utf8mb4：支持中文和 emoji；utf8mb4_unicode_ci：中文排序比较友好
            cur.execute(f"DROP DATABASE IF EXISTS `{DB_NAME}`")
            cur.execute(
                f"CREATE DATABASE `{DB_NAME}` "
                f"DEFAULT CHARACTER SET utf8mb4 "
                f"COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
        print(f"[OK] 数据库 `{DB_NAME}` 已创建")
    finally:
        conn.close()


def create_tables():
    """在 company_demo 里建 customers / orders 两张表。"""
    conn = get_connection(DB_NAME)
    try:
        with conn.cursor() as cur:
            # 客户表：一家公司一条记录
            cur.execute(
                """
                CREATE TABLE customers (
                    id          INT AUTO_INCREMENT PRIMARY KEY COMMENT '客户ID',
                    name        VARCHAR(100) NOT NULL COMMENT '客户名称',
                    city        VARCHAR(50)  NOT NULL COMMENT '所在城市',
                    industry    VARCHAR(50)  NOT NULL COMMENT '所属行业',
                    created_at  DATE         NOT NULL COMMENT '建档日期'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户表'
                """
            )

            # 订单表：customer_id 外键关联 customers.id
            # ON DELETE RESTRICT：有订单时不允许误删客户，练手时更安全
            cur.execute(
                """
                CREATE TABLE orders (
                    id           INT AUTO_INCREMENT PRIMARY KEY COMMENT '订单ID',
                    customer_id  INT            NOT NULL COMMENT '客户ID',
                    amount       DECIMAL(12, 2) NOT NULL COMMENT '订单金额（元）',
                    product      VARCHAR(100)   NOT NULL COMMENT '产品名称',
                    order_date   DATE           NOT NULL COMMENT '下单日期',
                    status       VARCHAR(20)    NOT NULL COMMENT '订单状态',
                    CONSTRAINT fk_orders_customer
                        FOREIGN KEY (customer_id) REFERENCES customers(id)
                        ON DELETE RESTRICT
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表'
                """
            )
        conn.commit()
        print("[OK] 表 customers、orders 已创建")
    finally:
        conn.close()


def seed_data():
    """插入 20 个客户 + 20 笔订单（数据尽量贴近真实业务场景）。"""
    customers = [
        ("华南智造科技有限公司", "广州", "制造业", "2023-01-15"),
        ("深圳云擎软件股份公司", "深圳", "互联网", "2023-02-08"),
        ("上海浦江金融信息服务有限公司", "上海", "金融", "2023-02-20"),
        ("北京康宁医疗器械有限公司", "北京", "医疗", "2023-03-05"),
        ("杭州绿源环保工程有限公司", "杭州", "环保", "2023-03-18"),
        ("成都蜀道物流有限公司", "成都", "物流", "2023-04-02"),
        ("武汉光谷教育科技有限公司", "武汉", "教育", "2023-04-16"),
        ("南京金陵零售连锁有限公司", "南京", "零售", "2023-05-01"),
        ("苏州精密电子有限公司", "苏州", "制造业", "2023-05-22"),
        ("西安丝路文旅发展有限公司", "西安", "文旅", "2023-06-10"),
        ("青岛海蓝海洋工程有限公司", "青岛", "制造业", "2023-06-28"),
        ("重庆两江汽车零部件有限公司", "重庆", "制造业", "2023-07-12"),
        ("天津滨海生物制药有限公司", "天津", "医疗", "2023-08-03"),
        ("长沙星城数字营销有限公司", "长沙", "互联网", "2023-08-19"),
        ("厦门鹭岛国际贸易有限公司", "厦门", "贸易", "2023-09-05"),
        ("合肥庐州新能源科技有限公司", "合肥", "能源", "2023-09-21"),
        ("郑州中原农业科技有限公司", "郑州", "农业", "2023-10-08"),
        ("大连星海航运服务有限公司", "大连", "物流", "2023-10-25"),
        ("福州闽都信息技术有限公司", "福州", "互联网", "2023-11-11"),
        ("昆明春城健康管理有限公司", "昆明", "医疗", "2023-12-01"),
    ]

    # customer_id 对应上面第 1~20 个客户（插入后 id 会是 1..20）
    orders = [
        (1, 128000.00, "工业物联网网关", "2024-01-12", "已完成"),
        (2, 86000.50, "云服务器年费套餐", "2024-01-28", "已完成"),
        (3, 215000.00, "风控数据分析平台", "2024-02-06", "已完成"),
        (4, 45300.00, "医用影像存储系统", "2024-02-18", "已发货"),
        (5, 67200.00, "废气在线监测设备", "2024-03-02", "已完成"),
        (6, 38900.00, "仓储管理系统授权", "2024-03-15", "处理中"),
        (7, 25600.00, "在线课程平台年费", "2024-03-27", "已完成"),
        (8, 91200.00, "门店收银一体机 x20", "2024-04-08", "已发货"),
        (9, 156800.00, "SMT 贴片检测设备", "2024-04-21", "已完成"),
        (10, 33400.00, "景区票务系统升级", "2024-05-05", "已取消"),
        (11, 178500.00, "海上监测浮标套件", "2024-05-19", "处理中"),
        (12, 142300.00, "汽车冲压件模具", "2024-06-03", "已完成"),
        (13, 98700.00, "生物反应器控制系统", "2024-06-16", "已发货"),
        (14, 42100.00, "投放效果分析看板", "2024-07-01", "已完成"),
        (15, 76500.00, "跨境电商 ERP 模块", "2024-07-14", "处理中"),
        (16, 203400.00, "储能柜电池管理系统", "2024-08-02", "已完成"),
        (17, 28900.00, "土壤墒情监测终端", "2024-08-20", "已发货"),
        (18, 55100.00, "船期协同调度系统", "2024-09-04", "已完成"),
        (19, 31800.00, "政务数据中台接口", "2024-09-22", "处理中"),
        (20, 44700.00, "健康档案管理软件", "2024-10-05", "已完成"),
    ]

    conn = get_connection(DB_NAME)
    try:
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO customers (name, city, industry, created_at) "
                "VALUES (%s, %s, %s, %s)",
                customers,
            )
            cur.executemany(
                "INSERT INTO orders (customer_id, amount, product, order_date, status) "
                "VALUES (%s, %s, %s, %s, %s)",
                orders,
            )
        conn.commit()
        print("[OK] 已插入 20 条客户、20 条订单")
    finally:
        conn.close()


def verify():
    """简单核对：打印行数，并各抽查几条，方便你肉眼确认。"""
    conn = get_connection(DB_NAME)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS cnt FROM customers")
            c_cnt = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) AS cnt FROM orders")
            o_cnt = cur.fetchone()["cnt"]
            print(f"[校验] customers = {c_cnt} 行, orders = {o_cnt} 行")

            print("\n--- customers 前 5 条 ---")
            cur.execute(
                "SELECT id, name, city, industry, created_at "
                "FROM customers ORDER BY id LIMIT 5"
            )
            for row in cur.fetchall():
                print(row)

            print("\n--- orders 前 5 条 ---")
            cur.execute(
                "SELECT id, customer_id, amount, product, order_date, status "
                "FROM orders ORDER BY id LIMIT 5"
            )
            for row in cur.fetchall():
                print(row)
    finally:
        conn.close()


def main():
    print("开始初始化 company_demo ...")
    create_database()
    create_tables()
    seed_data()
    verify()
    print("\n第 1 步完成。确认上面校验行数都是 20 后，把终端输出发给我，我们再做第 2 步。")


if __name__ == "__main__":
    main()
