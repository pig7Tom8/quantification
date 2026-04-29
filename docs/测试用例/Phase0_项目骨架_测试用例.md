# Phase 0 测试用例

## 1. 测试目标

验证项目骨架、SQLite 数据库、股票池过滤、股票基础信息与日 K 行情入库、本地 Markdown 日报，以及《10_数据源稳定性方案总结》在 Phase 0 范围内涉及的行情数据稳定性规则是否得到正确执行。

## 2. 测试范围

- 配置加载
- 数据库初始化
- Mock 数据采集
- 行情数据主备策略
- 行情数据失败重试与切源
- 股票池过滤
- 股票基础信息与日 K 行情入库
- 数据质量检查
- 行情数据不完整判定
- 股票基础信息兜底规则
- 行情历史数据兜底规则
- Tushare 股票基础信息按 PRD 复用当日快照
- 数据可信度分级与输出
- 调度服务基础行为
- 本地日报生成

本阶段不纳入执行范围，但后续阶段必须遵守的稳定性规则：

- 公告数据主备策略
- 新闻数据主备策略
- 财务数据主备策略
- 板块与概念数据主备策略
- 公告 / 新闻 / 财务 / 板块概念的降级运行规则

## 3. 前置条件

- Python 3.9+
- 仓库根目录存在 `.env`
- `USE_MOCK_PROVIDER=true`

## 4. 测试数据准备

- 使用系统内置 mock 股票数据
- 删除旧的 `data/quant_mvp.db` 与旧日报后重新执行

## 5. 测试步骤

### Case 1：主流程闭环

1. 执行 `python3 tests/phase0_acceptance.py`
2. 检查脚本输出是否为 `Phase 0 acceptance checks passed.`
3. 检查脚本是否同时验证：
   - 数据可信度为 `high`
   - 数据质量摘要包含 `missing=0 invalid=0`
   - 调度服务到点只执行一次
   - 股票基础信息与日 K 行情成功入库

### Case 2：命令行入口

1. 执行 `python3 main.py`
2. 检查终端是否输出交易日、可交易股票数、过滤股票数、日报路径
3. 检查终端是否输出数据可信度和数据质量摘要

### Case 3：`.env` 缺失容错

1. 临时将 `.env` 改名为 `.env.bak`
2. 执行 `USE_MOCK_PROVIDER=true python3 main.py`
3. 检查程序仍能成功结束
4. 将 `.env.bak` 恢复为 `.env`

### Case 4：关闭 mock provider 异常提示

1. 执行 `python3 tests/provider_fallback_checks.py`
2. 检查脚本输出是否为 `Provider fallback checks passed.`
3. 检查该测试覆盖的主备顺序是否符合 PRD：
   - 主源：AkShare
   - 备源：Tushare
   - 再备源：东方财富
4. 检查该测试覆盖的失败路径是否符合文档要求：
   - 主源失败后先重试
   - 再尝试备用源
   - 重试节奏符合 `10秒 -> 1分钟 -> 切换备用源`

### Case 5：真实 provider smoke test

1. 执行 `USE_MOCK_PROVIDER=false python3 main.py`
2. 检查程序是否按以下顺序尝试行情数据源：
   - 先 AkShare
   - 再 Tushare
   - 再 东方财富
3. 若外部数据源不可访问，则检查程序以可读方式输出“核心行情数据获取失败，已停止正式运行”
4. 若 `TUSHARE_TOKEN` 未配置，则检查输出中明确体现 `Tushare` 不可用原因，而不是静默跳过

### Case 6：行情数据不完整判定

1. 执行 `python3 tests/stability_phase0_checks.py`
2. 检查脚本是否覆盖“股票池数量正常，但仅返回部分行情数据”的测试输入
3. 检查系统是否将当日行情标记为不完整
4. 检查系统是否不继续正式输出

### Case 7：股票基础信息兜底

1. 执行 `python3 tests/stability_phase0_checks.py`
2. 检查脚本是否先准备上一日已存在的股票池数据，再模拟当天股票基础信息抓取失败
3. 检查系统是否可沿用昨日股票池继续运行
4. 检查结果是否降级为 `medium` 可信度

### Case 8：行情历史数据兜底

1. 执行 `python3 tests/stability_phase0_checks.py`
2. 检查脚本是否先准备历史行情数据，再模拟当天接口失败但历史数据仍可读取
3. 检查系统是否仅将历史数据作为辅助兜底
4. 若缺少今日收盘价 / 今日涨跌幅 / 今日成交额，则检查系统不生成正式日报

### Case 9：数据可信度分级

1. 执行 `python3 tests/stability_phase0_checks.py`
2. 检查脚本是否构造三类输入场景：
   - 行情完整率 > 98%，其余正常
   - 行情完整率 > 95%，但存在降级情况
   - 行情完整率 < 90% 或主备源全部失败
3. 检查系统是否分别输出 `high / medium / low`
4. 若输出为 `low`，检查结果中是否有明确提示

### Case 10：Tushare 股票基础信息按 PRD 复用当日快照

1. 执行 `python3 tests/tushare_stock_basic_reuse_checks.py`
2. 检查脚本是否验证数据库内已有“当日已更新”的股票池快照时，系统优先复用本地快照
3. 检查脚本是否验证复用快照后，股票池过滤仍会继续执行
4. 检查运行结果中是否保留“当日快照复用”提示，避免误判为接口正常返回

## 6. 预期结果

- 脚本自动完成数据库清理、两次运行和结果校验
- 程序成功结束并输出 Phase 0 汇总
- 数据库表自动创建完成
- 可交易股票成功入库
- 股票基础信息与日 K 行情成功入库
- 数据质量检查结果正常输出
- 行情数据不完整时会被识别出来
- 股票基础信息抓取失败时可沿用昨日股票池
- 行情接口失败时可区分“历史辅助兜底”与“不能正式输出”
- 日报文件生成成功
- 被过滤股票在日报中可见
- 同一交易日重复执行保持幂等
- 调度服务在到达设定时间时可触发任务，且同日不会重复执行
- `.env` 缺失时 mock 模式仍能运行
- 行情数据主备顺序符合 PRD：AkShare -> Tushare -> 东方财富
- 主源失败时会切到备源，而不是直接终止
- 失败重试与切源行为符合文档约定
- 数据可信度可输出高 / 中 / 低
- `Tushare stock_basic` 可按 PRD 复用当日股票池快照
- 真实 provider 不可用时应返回可读失败状态，而不是裸堆栈

## 7. 异常场景

- `.env` 缺失时仍可用默认配置跑 mock 模式
- 非 mock 模式下若主源与备源都不可用，应停止正式运行并输出可读错误信息
- 行情数据只返回少量股票时，不应视为正常完成
- 缺少今日收盘价 / 今日涨跌幅 / 今日成交额时，不应生成正式日报
- `TUSHARE_TOKEN` 缺失时，应明确提示 `Tushare` 不可用原因
- `Tushare stock_basic` 当日更新失败时，应优先复用已有股票池快照

## 8. 回归检查项

- 重复执行不会产生主键冲突
- 同一交易日重复执行为幂等更新

## 9. 测试结果记录

### 执行日期

- 2026-04-29

### 执行结果

- Case 1：通过
- Case 2：通过
- Case 3：通过
- Case 4：通过
- Case 5：已执行，系统已按 `AkShare -> Tushare -> 东方财富` 顺序尝试；当前环境下 AkShare 与东方财富返回远端连接中断，Tushare 因缺少 token 不可用，系统已按预期输出可读失败状态
- Case 6：通过
- Case 7：通过
- Case 8：通过
- Case 9：通过
- Case 10：通过

### 测试发现与修复记录

- 首次执行 Case 1 时失败，错误为 `ModuleNotFoundError: No module named 'backend'`
- 原因是直接运行 `tests/phase0_acceptance.py` 时，项目根目录未自动加入 Python 模块搜索路径
- 修复方式：在 `tests/phase0_acceptance.py` 中补充项目根路径注入 `sys.path`
- 修复后重新执行 Case 1，结果通过
- 其余 Case 在该修复完成后继续执行，结果均通过

### 结果摘要

- `tests/phase0_acceptance.py` 已验证数据库初始化、股票基础信息入库、日 K 行情入库、股票池过滤、日报生成和重复执行幂等性
- `tests/phase0_acceptance.py` 已验证数据可信度输出和数据质量摘要
- `tests/phase0_acceptance.py` 已验证每日调度服务的基础触发行为与同日防重复执行
- `tests/provider_fallback_checks.py` 已验证 PRD 规定的 AkShare -> Tushare -> 东方财富 顺序下，主源失败时后续备源会继续接管
- `python3 main.py` 已验证命令行入口可直接运行
- `.env` 临时移除后，显式指定 `USE_MOCK_PROVIDER=true` 仍可成功运行
- `USE_MOCK_PROVIDER=false` 的真实 provider smoke test 已执行，当前代码已按 PRD 顺序尝试 AkShare、Tushare、东方财富；但当前环境下 Tushare 缺少 token，AkShare 与东方财富返回远端连接中断，因此真实数据源仍未成功取回
- `tests/stability_phase0_checks.py` 已验证：
  - 行情数据不完整判定
  - 股票基础信息兜底
  - 行情历史数据兜底
  - `high / medium / low` 全部分级验证
- `tests/tushare_stock_basic_reuse_checks.py` 已验证：
  - 数据库内已有当日股票池快照时，系统优先复用本地快照
  - 复用快照后，股票池过滤仍会继续执行
- 真实链路现状：
  - `AkShare` 已可成功取回全市场行情并完成 Phase 0 主流程
  - `Tushare` 已按 PRD 复用当日股票池快照，但 `daily` 在当前交易日 `2026-04-29` 仍返回空结果，因此不能单独完成正式输出
  - `东方财富` 在当前环境下仍返回 `RemoteDisconnected('Remote end closed connection without response')`，包括直接调用 AkShare 自带的东财封装也复现该问题
