# Phase 0 测试用例

## 1. 测试目标

以主 PRD [股票量化系统_MVP修订版方案.md](/Users/zhouzheng/Desktop/workspace/subtree/agent_by_quantification/docs/prd/股票量化系统_MVP修订版方案.md:1) 为准，验证 Phase 0 项目骨架是否已经具备：

- 明确股票市场范围
- 确定数据源
- 建数据库表
- 搭定时任务
- 拉取 A 股基础数据
- 拉取日 K 数据
- 生成第一份本地 Markdown 日报

并验证主 PRD 第 3.1、4.1、17.1、17.2 与 Phase 0 直接相关的字段和过滤口径是否已在当前代码中落地。

## 2. 测试范围

- 配置加载
- SQLite 数据库初始化
- `stock_basic` / `daily_quote` 建表
- A 股基础数据入库
- 日 K 行情入库
- 股票池过滤规则执行
- 定时任务基础行为
- 本地 Markdown 日报生成
- Phase 0 范围内已落地的数据质量检查
- Phase 0 范围内已落地的主备数据源基础行为

本阶段不纳入“完成判定”，但当前代码已部分实现并可一并验证的内容：

- 行情主备顺序 `AkShare -> Tushare -> 东方财富`
- 行情失败重试与切源
- 行情不完整判定
- 股票基础信息当日快照复用
- 数据可信度输出

## 3. 前置条件

- Python 3.9+
- 仓库根目录存在 `.env`
- 若执行 mock 流程，允许使用默认 `USE_MOCK_PROVIDER=true`
- 若执行真实流程，需显式指定 `USE_MOCK_PROVIDER=false`

## 4. 测试数据准备

- 使用系统内置 mock 股票数据验证骨架闭环
- 删除旧的 `data/quant_mvp.db` 与旧日报后重新执行

## 5. 测试步骤

### Case 1：Phase 0 主流程闭环

1. 执行 `python3 tests/phase0_acceptance.py`
2. 检查脚本输出是否为 `Phase 0 acceptance checks passed.`
3. 检查该脚本是否验证：
   - `stock_basic` 已建表并入库
   - `daily_quote` 已建表并入库
   - A 股基础数据为全量入库，不只是可交易股票
   - 日报已生成
   - 重复执行保持幂等

### Case 2：命令行入口手动运行

1. 执行 `SCHEDULER_MODE=manual python3 main.py`
2. 检查终端是否输出：
   - 交易日
   - 可交易股票数
   - 被过滤股票数
   - 已入库行情数
   - 日报路径

### Case 3：定时任务基础行为

1. 执行 `python3 tests/phase0_acceptance.py`
2. 检查脚本是否验证：
   - 到达设定时间会执行一次任务
   - 同一天不会重复执行

### Case 4：股票池过滤规则

1. 执行 `python3 tests/phase0_acceptance.py`
2. 检查脚本是否验证：
   - `ST / *ST` 股票被过滤
   - 被过滤股票仍保留在 `stock_basic` 中
   - 被过滤股票会出现在日报摘要中

### Case 5：Phase 0 行情采集字段

1. 执行 `python3 tests/phase0_acceptance.py`
2. 检查脚本是否验证 `stock_basic` 至少已写入：
   - 股票代码
   - 股票名称
   - 行业
   - 总市值
   - 流通市值
3. 检查日报中的行业列是否不为空

### Case 6：`.env` 缺失容错

1. 临时将 `.env` 改名为 `.env.bak`
2. 执行 `USE_MOCK_PROVIDER=true SCHEDULER_MODE=manual python3 main.py`
3. 检查程序仍能成功结束
4. 将 `.env.bak` 恢复为 `.env`

### Case 7：真实 provider 主流程 smoke test

1. 执行 `USE_MOCK_PROVIDER=false SCHEDULER_MODE=manual python3 main.py`
2. 检查程序是否能完成一次真实主流程
3. 检查当前真实主流程是否以 `AkShare` 主源成功完成

### Case 8：当前代码已落地的稳定性检查

1. 执行：
   - `python3 tests/stability_phase0_checks.py`
   - `python3 tests/provider_fallback_checks.py`
   - `python3 tests/tushare_stock_basic_reuse_checks.py`
2. 检查脚本输出是否分别通过
3. 将这些结果记录为“当前代码已实现的附加稳定性检查”，但不作为主 PRD Phase 0 完成标志

## 6. 预期结果

- `stock_basic` 和 `daily_quote` 两张核心表成功创建
- A 股基础数据可入库
- 日 K 行情可入库
- 股票池过滤规则可执行
- 本地 Markdown 日报可生成
- 每日调度可运行
- 报告中行业字段不再为空
- 同一交易日重复执行保持幂等

## 7. 异常场景

- `.env` 缺失时 mock 模式仍可运行
- 非 mock 模式下若真实数据源失败，应返回可读错误信息
- 若当前运行模式为 `daily`，程序应进入常驻等待，而不是立即退出

## 8. 回归检查项

- 数据库重复初始化不会报错
- 同一交易日重复执行不会产生主键冲突
- 日报可重复生成并覆盖更新
- 新增字段不会破坏旧库初始化与升级

## 9. 测试结果记录

### 执行日期

- 2026-04-29

### 执行结果

- Case 1：通过
- Case 2：通过
- Case 3：通过
- Case 4：通过
- Case 5：通过
- Case 6：未在本轮重跑，沿用此前已通过记录
- Case 7：通过
- Case 8：通过

### 测试发现与修复记录

- 首次执行 `tests/phase0_acceptance.py` 时曾出现 `ModuleNotFoundError: No module named 'backend'`
- 原因是直接运行 `tests/` 下脚本时，项目根目录未自动加入 Python 模块搜索路径
- 修复方式：在测试脚本中补充项目根路径注入 `sys.path`
- 修复后重新执行，相关 case 已通过

### 本轮执行摘要

- `python3 tests/phase0_acceptance.py`：通过
- `python3 tests/stability_phase0_checks.py`：通过
- `python3 tests/provider_fallback_checks.py`：通过
- `python3 tests/tushare_stock_basic_reuse_checks.py`：通过
- `SCHEDULER_MODE=manual python3 main.py`：通过
- `USE_MOCK_PROVIDER=false SCHEDULER_MODE=manual python3 main.py`：通过，当前真实主流程由 `AkShare` 成功完成

### 说明

- 以主 PRD 的 Phase 0 范围判断，当前项目骨架闭环已跑通
- 当前代码额外实现了一部分稳定性能力，并已通过附加测试
- 当前仍未完全补齐的主 PRD 采集字段主要是 `概念`
