# -*- coding: utf-8 -*-
"""配置文件与测试数据读取。"""

import os

import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


def read_yaml(*path_parts):
    path = os.path.join(BASE_DIR, *path_parts)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_config():
    """按 env 取当前环境的配置。"""
    cfg = read_yaml("config", "config.yaml")
    return cfg[cfg["env"]]


def load_case(filename):
    """读取 data/ 下与用例文件同名的数据文件。"""
    return read_yaml("data", filename)
