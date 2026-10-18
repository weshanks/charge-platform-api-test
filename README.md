# charge-platform-api-test

充电桩运营平台 · 接口自动化测试实践（个人练手项目）

## 项目说明

这是一套面向"充电桩运营平台"业务场景的接口自动化测试工程实践。

**说明：本项目为个人学习与技术练手性质，非公司商业项目。** 业务场景为自行设计的模拟场景，被测接口由本项目自带的 mock 服务提供，目的是完整实践接口自动化的工程化落地。

## 为什么做这个

1. 系统实践 Python 接口自动化的工程化做法：分层设计、数据驱动、接口关联、数据库校验、CI 集成；
2. 跑通"设计用例 → 编写脚本 → 执行 → 报告 → 质量门禁"的完整闭环；
3. 沉淀一套可复用的框架模板，便于将来快速迁移到实际业务。

## 被测业务场景

模拟充电桩运营平台的三个核心域：

| 业务域 | 关键场景 | 重点测试点 |
|--------|---------|-----------|
| 登录鉴权 | 获取 token、token 失效 | 正常登录、账号密码错误、缺参、未携带 token 访问受保护接口 |
| 充电主流程 | 扫码启动充电、停止充电 | 参数校验、设备/订单状态流转、重复下发、鉴权失败 |
| 订单管理 | 订单查询、金额结算 | 金额计算与四舍五入、订单状态机、分页查询、数据库落库一致性 |
| 设备管理 | 设备档案、状态查询 | 增删改查、编码重复、状态取值合法性、分页 |

金额规则（简化设计）：`应付 = 电量 × (电费单价 1.2 + 服务费单价 0.4) - 优惠`，各分项四舍五入保留 2 位。

## 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.x |
| 接口请求 | Requests |
| 测试框架 | Pytest（fixture / parametrize / markers） |
| 数据驱动 | YAML |
| 报告 | Allure-pytest |
| 数据库校验 | sqlite3（默认，开箱即跑）/ PyMySQL |
| 持续集成 | Jenkins Pipeline |
| 被测服务 | Flask + SQLite（自建 mock，保证 clone 即跑） |

## 项目结构

```
charge-platform-api-test/
├── common/                  # 公共封装
│   ├── request_client.py    # 请求封装：超时/日志/鉴权注入/异常兜底
│   ├── assert_util.py       # 断言封装：状态码/业务码/字段/金额/数据库比对
│   ├── db_client.py         # 数据库操作封装（sqlite 与 mysql 同一套占位符）
│   └── yaml_util.py         # 配置与测试数据读取
├── api/                     # 接口层：只负责发请求，不含断言
│   ├── login_api.py
│   ├── order_api.py
│   └── device_api.py
├── testcase/                # 用例层：只做业务编排 + 断言
│   ├── test_login.py
│   ├── test_device.py
│   └── test_order.py
├── data/                    # 测试数据，与用例文件同名对应
│   ├── test_login.yaml
│   ├── test_device.yaml
│   └── test_order.yaml
├── config/
│   └── config.yaml          # 环境配置：host、账号、数据库连接
├── conftest.py              # fixture：登录态 token、被测服务自启动、运行时变量
├── pytest.ini               # 用例收集规则、marker、默认参数
├── Jenkinsfile
├── requirements.txt
├── mock_server/             # 被测服务（自建 mock，保证 clone 即跑）
└── README.md
```

## 快速开始

### 环境要求

- Python 3.8+
- Allure 命令行工具（可选，仅生成 HTML 报告时需要）

数据库默认使用 SQLite，无需额外安装；切换 MySQL 时修改 `config/config.yaml` 中 `db.type` 即可。

### 安装

```bash
git clone {{你的仓库地址}}
cd charge-platform-api-test
pip install -r requirements.txt
```

### 配置

编辑 `config/config.yaml`：

```yaml
env: test
test:
  base_url: http://127.0.0.1:5000
  account:
    username: admin
    password: admin123
  db:
    type: sqlite
    path: mock_server/charge_platform.db
```

### 运行

```bash
# 运行全部用例（被测服务未启动时会自动拉起 mock_server）
pytest

# 按 marker 运行冒烟用例
pytest -m smoke

# 生成并查看 Allure 报告
pytest --alluredir=./allure-results
allure serve ./allure-results
```

## 核心设计说明

### 1. 分层设计

采用「接口层 → 用例层 → 数据层」三层解耦：

- `api/` 只负责发请求并返回响应，不含断言；
- `testcase/` 只负责业务编排和断言，不关心请求细节；
- `data/` 存放测试输入与预期结果，一条数据对应一个场景。

收益：接口字段变动时只改 `api` 层和数据文件，用例层基本不用动，维护成本可控。

### 2. 请求封装

在 `common/request_client.py` 统一处理超时、请求/响应日志、鉴权注入（登录后 token 复用）和异常兜底。
好处是用例里不用各自关心"怎么发请求"，也方便统一排查和加埋点。

### 3. 数据驱动

同一接口的正常/异常/边界场景用 YAML 描述，`parametrize` 驱动。
例如金额场景，用「电量区间 × 优惠券」做成组合数据表，边界值覆盖 0 度、负电量、超上限电量、0.01 度极小电量。

### 4. 接口关联

解决用例间的依赖（如先登录取 token、先启动充电再停止）：通过 `conftest.py` 的 fixture 传递，
并把上一步响应中的关键字段（如 order_no、device_code）写入运行时变量 `ctx` 供后续用例引用，避免硬编码和用例耦合。

### 5. 数据库双重断言

接口返回成功不代表数据正确，因此关键场景都加了数据库校验层：
比对「接口返回字段 == 数据库落库字段」，并延伸到关联表（订单表 `t_order` + 结算流水表 `t_settle`）。
金额、状态机这类核心场景尤其依赖这一层——很多"表面成功但落库错误"的问题只有这层能发现。

### 6. Allure 报告

用 `@allure.feature / story / title` 标注业务层级，报告中可按模块查看通过率、失败原因和请求响应详情，排查效率高于纯文本日志。

## 用例与覆盖情况

| 模块 | 接口数 | 自动化用例数 | 说明 |
|------|--------|-------------|------|
| 登录/鉴权 | 1 | 4 | 正常登录、密码错误、账号不存在、缺参 |
| 设备管理 | 5 | 7 | 新增/重复编码/缺参/分页/改状态/非法状态/删除 |
| 充电主流程 | 2 | 6 | 启动成功、设备忙、设备不存在、缺参、未鉴权、金额结算 |
| 订单管理 | 2 | 8 | 金额计算 4 组 + 非法电量 3 组 + 重复停止 + 查询校验 |
| 合计 | 10 | 25 | 一次全量执行约 5 秒 |

## 持续集成

Jenkins Pipeline 片段：

```groovy
stage('接口自动化') {
    steps {
        sh 'pytest --alluredir=./allure-results'
    }
    post {
        always {
            allure includeProperties: false, results: [[path: 'allure-results']]
        }
    }
}
```

质量门禁：核心用例通过率 100%、整体 ≥ 98% 才允许继续；失败先区分为环境问题、脚本问题还是真实缺陷，**不允许靠删用例拉通过率**。

## 已知不足与后续计划

- 被测服务为简化 mock，与真实充电桩业务（计费档位、峰谷电价、退款）还有差距，后续补充时段电价与退款场景；
- 报告暂未接入企业微信/邮件通知；
- 计划把重复的数据准备逻辑抽象成更通用的工具。

## 说明

本项目为个人学习练手性质，业务场景自行设计，如与真实业务形态相似属通用性所致。
