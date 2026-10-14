# -*- coding: utf-8 -*-
"""
第 2 步：自然语言 → SQL → 查 MySQL

流程：
1. 从环境变量 DEEPSEEK_API_KEY 读取密钥（不写死在代码里）
2. 连接本机 company_demo 库
3. 从 information_schema 读出 customers / orders 的字段名、类型
4. 命令行循环：用户提问 → DeepSeek 生成一条 SELECT → pymysql 执行 → 打印结果
5. 执行失败时，把错误和原问题再发给 DeepSeek，让它修正后重试一次
6. 输入 exit 或 quit 退出

运行前请先设置环境变量，见文件末尾的说明。
"""

import os
import re
import sys

import pymysql
from openai import OpenAI  # DeepSeek 兼容 OpenAI 的 SDK 接口

# ---------- 本机 MySQL（和第 1 步同一套）----------
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "abc123456"
DB_NAME = "company_demo"

# DeepSeek 官方兼容 OpenAI 的地址和模型名
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"


def get_api_key():
    """从环境变量读 Key。读不到就立刻退出，避免把空密钥发出去。"""
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        print("[错误] 未找到环境变量 DEEPSEEK_API_KEY")
        print("请先设置后再运行，PowerShell 示例：")
        print('  $env:DEEPSEEK_API_KEY = "你的密钥"')
        print("  python text2sql.py")
        sys.exit(1)
    return key


def connect_db():
    """连接练习库 company_demo。"""
    print("[1] 正在连接本机 MySQL ...")
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    print(f"[1] 已连接到库 `{DB_NAME}`")
    return conn


def load_schema(conn):
    """
    从 information_schema 读取两张表的字段名和类型。
    把这些信息塞进 prompt，模型才知道该用哪些列名，减少胡编。
    """
    print("[2] 正在读取 customers、orders 的表结构 ...")
    sql = """
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, COLUMN_COMMENT
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME IN ('customers', 'orders')
        ORDER BY TABLE_NAME, ORDINAL_POSITION
    """
    with conn.cursor() as cur:
        cur.execute(sql, (DB_NAME,))
        rows = cur.fetchall()

    if not rows:
        print("[错误] 没读到表结构。请先运行 python init_db.py")
        sys.exit(1)

    lines = []
    current_table = None
    for row in rows:
        table = row["TABLE_NAME"]
        if table != current_table:
            lines.append(f"\n表 {table}:")
            current_table = table
        comment = row["COLUMN_COMMENT"] or ""
        extra = f"  -- {comment}" if comment else ""
        lines.append(f"  - {row['COLUMN_NAME']} ({row['DATA_TYPE']}){extra}")

    schema_text = "\n".join(lines).strip()
    print("[2] 表结构已准备好：")
    print(schema_text)
    return schema_text


def make_client(api_key):
    """创建 DeepSeek 客户端。接口和 OpenAI 一样，换 base_url 即可。"""
    print("[3] 正在初始化 DeepSeek 客户端 ...")
    client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
    print("[3] 客户端就绪")
    return client


def build_system_prompt(schema_text):
    """系统提示：告诉模型库长什么样，以及必须只输出一条 SELECT。"""
    return f"""你是 Text-to-SQL 助手。根据用户的中文问题，生成 MySQL 8.0 可执行的查询。

数据库名：{DB_NAME}
表结构：
{schema_text}

硬性规则：
1. 只输出一条 SQL，必须是 SELECT（或 WITH ... SELECT），不要 INSERT/UPDATE/DELETE/DROP。
2. 不要解释，不要 markdown，不要代码围栏，不要前后缀文字。
3. 只用上面出现的表名和字段名。
4. 中文城市、行业、状态等条件要用中文匹配（例如 广州、制造业、已完成）。
5. 金额字段是 DECIMAL，聚合可用 SUM/AVG/COUNT。
"""


def ask_deepseek(client, messages):
    """调用一次 DeepSeek，返回模型原文。"""
    print("[模型] 正在请求 DeepSeek 生成 SQL ...")
    resp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=messages,
        temperature=0,  # 生成 SQL 时尽量稳定、少发挥
    )
    text = (resp.choices[0].message.content or "").strip()
    print("[模型] 已收到回复")
    return text


def extract_sql(text):
    """
    模型有时仍会包 ```sql ... ```，这里剥掉围栏，只留下 SQL。
    这是防御性处理，prompt 已经要求不要 markdown。
    """
    fenced = re.search(r"```(?:sql)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fenced:
        text = fenced.group(1)
    # 只取第一句，避免后面再跟解释
    sql = text.strip().rstrip(";").strip()
    return sql + ";"


def is_safe_select(sql):
    """只允许查询语句，防止模型偶尔生成危险 SQL。"""
    compact = re.sub(r"\s+", " ", sql).strip()
    # 去掉末尾分号再判断
    head = compact.lstrip().rstrip(";").lstrip()
    return bool(re.match(r"(?is)^(SELECT|WITH)\b", head))


def print_rows(rows):
    """把查询结果打印成简单表格。"""
    if not rows:
        print("[结果] 查询成功，但没有匹配的行。")
        return

    columns = list(rows[0].keys())
    # 每列宽度：表头和各行取最大长度，上限 40，避免超长撑爆终端
    widths = []
    for col in columns:
        longest = len(str(col))
        for row in rows:
            longest = max(longest, len(str(row[col])))
        widths.append(min(longest, 40))

    def fmt_cell(value, width):
        s = str(value)
        if len(s) > width:
            s = s[: width - 1] + "…"
        return s.ljust(width)

    header = " | ".join(fmt_cell(col, w) for col, w in zip(columns, widths))
    line = "-+-".join("-" * w for w in widths)
    print("[结果] 共", len(rows), "行")
    print(header)
    print(line)
    for row in rows:
        print(" | ".join(fmt_cell(row[col], w) for col, w in zip(columns, widths)))


def run_select(conn, sql):
    """执行 SELECT，返回 (成功?, 行列表或错误信息)。"""
    print("[执行] SQL =", sql)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
        print("[执行] 成功")
        return True, rows
    except Exception as exc:
        # 执行失败时回滚，避免连接停在错误状态
        conn.rollback()
        err = str(exc)
        print("[执行] 失败：", err)
        return False, err


def nl_to_sql_and_query(conn, client, system_prompt, question):
    """
    一次完整问答：
    - 先生成 SQL 并执行
    - 失败则把错误 + 原问题发给模型，修正后再执行一次
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    raw = ask_deepseek(client, messages)
    sql = extract_sql(raw)
    print("[解析] 得到 SQL：", sql)

    if not is_safe_select(sql):
        print("[拦截] 模型没有返回 SELECT，已拒绝执行：", sql)
        return

    ok, payload = run_select(conn, sql)
    if ok:
        print_rows(payload)
        return

    # ---------- 失败后重试一次 ----------
    print("[重试] 把错误信息和原问题发给 DeepSeek，请它修正 SQL ...")
    messages.append({"role": "assistant", "content": sql})
    messages.append(
        {
            "role": "user",
            "content": (
                f"刚才这条 SQL 执行失败。\n"
                f"原问题：{question}\n"
                f"错误信息：{payload}\n"
                f"请只返回一条修正后的 SELECT SQL，不要解释。"
            ),
        }
    )

    raw2 = ask_deepseek(client, messages)
    sql2 = extract_sql(raw2)
    print("[解析] 修正后的 SQL：", sql2)

    if not is_safe_select(sql2):
        print("[拦截] 修正结果仍不是 SELECT，已拒绝执行：", sql2)
        return

    ok2, payload2 = run_select(conn, sql2)
    if ok2:
        print_rows(payload2)
    else:
        print("[结束] 重试后仍然失败，请换一种问法，或检查表结构。")


def main():
    print("======== Text-to-SQL 练习工具 ========")
    api_key = get_api_key()
    conn = connect_db()
    try:
        schema_text = load_schema(conn)
        client = make_client(api_key)
        system_prompt = build_system_prompt(schema_text)

        print()
        print("[就绪] 请输入中文问题，例如：广州有哪些客户？")
        print("[就绪] 输入 exit 或 quit 退出。")
        print("======================================")

        while True:
            try:
                question = input("\n你问> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[退出] 再见。")
                break

            if not question:
                continue
            if question.lower() in ("exit", "quit"):
                print("[退出] 再见。")
                break

            print("[问题]", question)
            try:
                nl_to_sql_and_query(conn, client, system_prompt, question)
            except Exception as exc:
                # 网络/API 异常不要把整个程序打崩
                print("[错误] 这一轮失败：", exc)
                print("[提示] 可再问一次，或检查网络 / API Key。")
    finally:
        conn.close()
        print("[关闭] 数据库连接已断开")


if __name__ == "__main__":
    main()
