# Phase 1 因子评分测试用例

## 测试依据

- 主 PRD：[股票量化系统_MVP修订版方案.md](../prd/股票量化系统_MVP修订版方案.md)
- 补充文档：[02_Phase1_因子评分.md](../开发步骤/02_Phase1_因子评分.md)

## 阶段范围

```text
- 实现趋势因子
- 实现资金因子
- 实现基础财务因子
- 实现风险因子
- 实现综合评分
- 实现 S/A/B/C/D/R 评级
- 输出每日 Top 50 股票
```

资讯分和拥挤度调整属于后续阶段，本阶段按主 PRD 公式保留字段，分值记为 0。

## Case 1：评级区间

步骤：

```bash
python3 tests/phase1_acceptance.py
```

期望：

```text
85 - 100 => S
75 - 84 => A
65 - 74 => B
50 - 64 => C
< 50 => D
风险触发 => R
```

结果：通过。

## Case 2：因子评分入库

步骤：

```bash
python3 tests/phase1_acceptance.py
```

期望：

```text
factor_score 写入当日评分记录
trend_score / money_score / fundamental_score / risk_score 有值
news_score = 0
crowding_adjustment = 0
```

结果：通过。

## Case 3：策略信号输出

步骤：

```bash
python3 tests/phase1_acceptance.py
```

期望：

```text
strategy_signals 写入 Top50 / S / A / 风险剔除相关信号
```

结果：通过。

## Case 4：评分日报生成

步骤：

```bash
python3 tests/phase1_acceptance.py
```

期望：

```text
生成 factor_report_YYYY-MM-DD.md
包含 Top 50 股票、S 级股票、A 级股票、风险剔除股票
```

结果：通过。

## 执行记录

```text
2026-04-30：新增 Phase 1 自动化验收脚本，并完成 mock 链路验收。
```
