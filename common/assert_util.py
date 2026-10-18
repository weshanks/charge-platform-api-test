# -*- coding: utf-8 -*-
"""断言封装：HTTP 状态、业务码、字段取值、数据库落库比对。"""

from decimal import Decimal


def _num(value):
    """金额统一按 2 位小数比较，避免浮点误差导致误判。"""
    return round(float(Decimal(str(value))), 2)


def assert_status(resp, expected=200):
    assert resp.status_code == expected, \
        f"HTTP 状态码不符：期望 {expected}，实际 {resp.status_code}，响应={resp.text}"


def assert_code(resp, expected=0):
    body = resp.json()
    assert body["code"] == expected, \
        f"业务码不符：期望 {expected}，实际 {body['code']}，msg={body.get('msg')}"


def assert_api_ok(resp, expected_code=0, expected_status=200):
    assert_status(resp, expected_status)
    assert_code(resp, expected_code)


def assert_equal(actual, expected, msg=""):
    assert actual == expected, f"{msg} 不一致：期望 {expected}，实际 {actual}"


def assert_amount(actual, expected, msg=""):
    assert _num(actual) == _num(expected), \
        f"{msg} 金额不一致：期望 {_num(expected)}，实际 {_num(actual)}"


def assert_db_field(db, sql, args, field, expected, msg=""):
    """数据库断言：查不到记录或字段不符都直接失败。"""
    row = db.query_one(sql, args)
    assert row is not None, f"{msg} 数据库中未查到记录：sql={sql} args={args}"
    assert row.get(field) == expected, \
        f"{msg} 数据库字段 {field} 不符：期望 {expected}，实际 {row.get(field)}"


def assert_db_amount(db, sql, args, field, expected, msg=""):
    row = db.query_one(sql, args)
    assert row is not None, f"{msg} 数据库中未查到记录：sql={sql} args={args}"
    assert_amount(row.get(field), expected, msg + f" 数据库字段 {field}")


def assert_db_count(db, sql, args, expected, msg=""):
    rows = db.query_all(sql, args)
    assert len(rows) == expected, \
        f"{msg} 记录数不符：期望 {expected}，实际 {len(rows)}"
