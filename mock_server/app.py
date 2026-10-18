# -*- coding: utf-8 -*-
"""充电桩运营平台 Mock 服务（Flask + SQLite）

说明：本项目为个人练手性质，被测接口由本文件提供，clone 下来即可运行。
简化后的业务规则：
- 金额 = 电量 × (电费单价 + 服务费单价) - 优惠，各分项四舍五入保留 2 位
- 订单状态机：charging -> finished
- 设备状态机：idle -> charging -> idle

启动：python mock_server/app.py   默认 http://127.0.0.1:5000
"""

import os
import sqlite3
import time
import uuid

from flask import Flask, jsonify, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "charge_platform.db")

PRICE_ELEC = 1.2        # 电费单价（元/度）
PRICE_SERVICE = 0.4     # 服务费单价（元/度）
MAX_KWH = 1000          # 单次充电电量上限
TOKEN_TTL = 3600        # token 有效期（秒）

app = Flask(__name__)
TOKENS = {}             # token -> 签发时间

# 业务码：0 成功；1001 登录失败；1002 未鉴权；2001 设备不存在；
#        2002 状态不允许；2003 设备编码重复；3001 参数非法
INIT_SQL = """
CREATE TABLE IF NOT EXISTS t_device (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  device_code  TEXT UNIQUE NOT NULL,
  station_name TEXT NOT NULL,
  status       TEXT NOT NULL DEFAULT 'idle',
  power        REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS t_order (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  order_no    TEXT UNIQUE NOT NULL,
  device_code TEXT NOT NULL,
  user_id     TEXT NOT NULL,
  status      TEXT NOT NULL,
  kwh         REAL DEFAULT 0,
  amount      REAL DEFAULT 0,
  coupon      REAL DEFAULT 0,
  create_time TEXT NOT NULL,
  finish_time TEXT
);
CREATE TABLE IF NOT EXISTS t_settle (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  order_no    TEXT NOT NULL,
  elec_fee    REAL NOT NULL,
  service_fee REAL NOT NULL,
  coupon      REAL NOT NULL,
  pay_amount  REAL NOT NULL,
  settle_time TEXT NOT NULL
);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(INIT_SQL)
    conn.executemany(
        "INSERT OR IGNORE INTO t_device(device_code, station_name, status, power) VALUES (?,?,?,?)",
        [("CD0001", "中原万达充电站", "idle", 120),
         ("CD0002", "高新万达充电站", "idle", 60)],
    )
    conn.commit()
    conn.close()


def ok(data=None):
    return jsonify({"code": 0, "msg": "ok", "data": data if data is not None else {}})


def fail(code, msg, http_status=200):
    return jsonify({"code": code, "msg": msg, "data": {}}), http_status


def authorized():
    token = request.headers.get("Authorization")
    if not token or token not in TOKENS:
        return False
    if time.time() - TOKENS[token] > TOKEN_TTL:
        TOKENS.pop(token, None)
        return False
    return True


def require_param(body, *fields):
    missing = [f for f in fields if body.get(f) in (None, "")]
    return missing


@app.route("/health")
def health():
    return jsonify({"status": "up"})


@app.route("/api/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    if require_param(body, "username", "password"):
        return fail(3001, "username/password 不能为空")

    if body["username"] == "admin" and body["password"] == "admin123":
        token = "tk_" + uuid.uuid4().hex
        TOKENS[token] = time.time()
        return ok({"token": token, "expires_in": TOKEN_TTL})

    return fail(1001, "用户名或密码错误")


@app.route("/api/device", methods=["POST"])
def add_device():
    if not authorized():
        return fail(1002, "未登录或 token 已失效", 401)
    body = request.get_json(silent=True) or {}
    if require_param(body, "device_code", "station_name", "power"):
        return fail(3001, "device_code/station_name/power 不能为空")

    conn = get_conn()
    exists = conn.execute(
        "SELECT 1 FROM t_device WHERE device_code=?", (body["device_code"],)
    ).fetchone()
    if exists:
        conn.close()
        return fail(2003, "设备编码已存在")

    conn.execute(
        "INSERT INTO t_device(device_code, station_name, status, power) VALUES (?,?,?,?)",
        (body["device_code"], body["station_name"], "idle", float(body["power"])),
    )
    conn.commit()
    conn.close()
    return ok({"device_code": body["device_code"], "status": "idle"})


@app.route("/api/device/list", methods=["GET"])
def device_list():
    if not authorized():
        return fail(1002, "未登录或 token 已失效", 401)
    page = int(request.args.get("page", 1))
    size = int(request.args.get("size", 10))
    conn = get_conn()
    total = conn.execute("SELECT COUNT(1) c FROM t_device").fetchone()["c"]
    rows = conn.execute(
        "SELECT * FROM t_device ORDER BY id LIMIT ? OFFSET ?",
        (size, (page - 1) * size),
    ).fetchall()
    conn.close()
    return ok({"total": total, "page": page, "size": size,
               "list": [dict(r) for r in rows]})


@app.route("/api/device/<device_code>", methods=["GET", "PUT", "DELETE"])
def device_detail(device_code):
    if not authorized():
        return fail(1002, "未登录或 token 已失效", 401)
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM t_device WHERE device_code=?", (device_code,)
    ).fetchone()
    if not row:
        conn.close()
        return fail(2001, "设备不存在")

    if request.method == "GET":
        conn.close()
        return ok(dict(row))

    if request.method == "PUT":
        status = (request.get_json(silent=True) or {}).get("status")
        if status not in ("idle", "charging", "fault", "offline"):
            conn.close()
            return fail(3001, "status 取值非法")
        conn.execute("UPDATE t_device SET status=? WHERE device_code=?", (status, device_code))
        conn.commit()
        conn.close()
        return ok({"device_code": device_code, "status": status})

    conn.execute("DELETE FROM t_device WHERE device_code=?", (device_code,))
    conn.commit()
    conn.close()
    return ok({"device_code": device_code})


@app.route("/api/charge/start", methods=["POST"])
def charge_start():
    if not authorized():
        return fail(1002, "未登录或 token 已失效", 401)
    body = request.get_json(silent=True) or {}
    if require_param(body, "device_code", "user_id"):
        return fail(3001, "device_code/user_id 不能为空")

    conn = get_conn()
    device = conn.execute(
        "SELECT * FROM t_device WHERE device_code=?", (body["device_code"],)
    ).fetchone()
    if not device:
        conn.close()
        return fail(2001, "设备不存在")
    if device["status"] != "idle":
        conn.close()
        return fail(2002, "设备非空闲，无法启动充电")

    order_no = "NO" + uuid.uuid4().hex[:16].upper()
    conn.execute(
        "INSERT INTO t_order(order_no, device_code, user_id, status, create_time)"
        " VALUES (?,?,?,?,?)",
        (order_no, body["device_code"], body["user_id"], "charging",
         time.strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.execute("UPDATE t_device SET status='charging' WHERE device_code=?",
                 (body["device_code"],))
    conn.commit()
    conn.close()
    return ok({"order_no": order_no, "status": "charging"})


@app.route("/api/charge/stop", methods=["POST"])
def charge_stop():
    if not authorized():
        return fail(1002, "未登录或 token 已失效", 401)
    body = request.get_json(silent=True) or {}
    if require_param(body, "order_no", "kwh"):
        return fail(3001, "order_no/kwh 不能为空")

    try:
        kwh = float(body["kwh"])
    except (TypeError, ValueError):
        return fail(3001, "kwh 必须为数字")
    coupon = float(body.get("coupon") or 0)
    if kwh <= 0 or kwh > MAX_KWH or coupon < 0:
        return fail(3001, "电量或优惠金额非法")

    conn = get_conn()
    order = conn.execute(
        "SELECT * FROM t_order WHERE order_no=?", (body["order_no"],)
    ).fetchone()
    if not order:
        conn.close()
        return fail(2001, "订单不存在")
    if order["status"] != "charging":
        conn.close()
        return fail(2002, "订单状态非充电中，无法停止")

    elec_fee = round(kwh * PRICE_ELEC, 2)
    service_fee = round(kwh * PRICE_SERVICE, 2)
    if coupon > elec_fee + service_fee:
        conn.close()
        return fail(3001, "优惠金额不能超过应付金额")
    pay_amount = round(elec_fee + service_fee - coupon, 2)
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    conn.execute(
        "UPDATE t_order SET status='finished', kwh=?, amount=?, coupon=?, finish_time=? "
        "WHERE order_no=?",
        (kwh, pay_amount, coupon, now, body["order_no"]),
    )
    conn.execute("UPDATE t_device SET status='idle' WHERE device_code=?",
                 (order["device_code"],))
    conn.execute(
        "INSERT INTO t_settle(order_no, elec_fee, service_fee, coupon, pay_amount, settle_time)"
        " VALUES (?,?,?,?,?,?)",
        (body["order_no"], elec_fee, service_fee, coupon, pay_amount, now),
    )
    conn.commit()
    conn.close()
    return ok({"order_no": body["order_no"], "kwh": kwh, "elec_fee": elec_fee,
               "service_fee": service_fee, "coupon": coupon,
               "amount": pay_amount, "status": "finished"})


@app.route("/api/order/<order_no>", methods=["GET"])
def order_detail(order_no):
    if not authorized():
        return fail(1002, "未登录或 token 已失效", 401)
    conn = get_conn()
    row = conn.execute("SELECT * FROM t_order WHERE order_no=?", (order_no,)).fetchone()
    conn.close()
    if not row:
        return fail(2001, "订单不存在")
    return ok(dict(row))


@app.route("/api/order/list", methods=["GET"])
def order_list():
    if not authorized():
        return fail(1002, "未登录或 token 已失效", 401)
    user_id = request.args.get("user_id")
    status = request.args.get("status")
    page = int(request.args.get("page", 1))
    size = int(request.args.get("size", 10))

    sql = "SELECT * FROM t_order WHERE 1=1"
    args = []
    if user_id:
        sql += " AND user_id=?"
        args.append(user_id)
    if status:
        sql += " AND status=?"
        args.append(status)

    conn = get_conn()
    total = conn.execute(
        sql.replace("SELECT *", "SELECT COUNT(1) c"), args
    ).fetchone()["c"]
    rows = conn.execute(
        sql + " ORDER BY id LIMIT ? OFFSET ?", args + [size, (page - 1) * size]
    ).fetchall()
    conn.close()
    return ok({"total": total, "page": page, "size": size,
               "list": [dict(r) for r in rows]})


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=False)
