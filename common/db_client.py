# -*- coding: utf-8 -*-
"""数据库封装：用于接口返回与数据库落库的双重断言。

sqlite 与 mysql 共用一套 SQL 占位符（%s），内部按类型转换，
这样测试脚本换库不用改。
"""

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class DBClient:
    def __init__(self, db_conf):
        self.type = db_conf.get("type", "sqlite")
        if self.type == "sqlite":
            path = db_conf["path"]
            if not os.path.isabs(path):
                path = os.path.join(BASE_DIR, path)
            self.conn = sqlite3.connect(path)
            self.conn.row_factory = sqlite3.Row
        else:
            import pymysql
            self.conn = pymysql.connect(
                host=db_conf["host"],
                port=int(db_conf["port"]),
                user=db_conf["user"],
                password=db_conf["password"],
                database=db_conf["database"],
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True,
            )

    def _sql(self, sql):
        return sql.replace("%s", "?") if self.type == "sqlite" else sql

    def query_one(self, sql, args=None):
        cur = self.conn.cursor()
        cur.execute(self._sql(sql), args or ())
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else None

    def query_all(self, sql, args=None):
        cur = self.conn.cursor()
        cur.execute(self._sql(sql), args or ())
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]

    def execute(self, sql, args=None):
        cur = self.conn.cursor()
        cur.execute(self._sql(sql), args or ())
        self.conn.commit()
        cur.close()

    def close(self):
        self.conn.close()
