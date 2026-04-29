# Phase 1：因子评分

## 阶段目标

让系统具备每日选股和评级能力，收盘后可以输出 Top 50 股票、S 级股票、A 级股票和风险剔除股票。

## 对应原方案内容

- 因子体系
- 技术趋势因子
- 资金强度因子
- 基本面因子
- 风险因子
- 综合评分与评级
- 策略设计中的风险剔除逻辑
- Phase 1：因子评分，2 周

## 本阶段范围

```text
- 实现趋势因子
- 实现资金因子
- 实现基础财务因子
- 实现风险因子
- 实现综合评分
- 实现 S/A/B/C/D/R 评级
- 输出每日 Top 50 股票
```

## 分数结构

```text
Score = TrendScore
      + MoneyScore
      + FundamentalScore
      + NewsScore
      + RiskScore
      + CrowdingAdjustment
```

本阶段重点先实现：

```text
- TrendScore
- MoneyScore
- FundamentalScore
- RiskScore
- Rating
```

资讯分和拥挤度调整在后续阶段补齐。

## 需要落地的模块

```text
backend/
- factors/trend_factor.py
- factors/money_factor.py
- factors/fundamental_factor.py
- factors/risk_factor.py
- scoring/score_engine.py
- strategies/risk_filter_strategy.py
```

## 关键规则

### 趋势分

```text
0 ~ 30 分
```

### 资金分

```text
0 ~ 25 分
```

### 基本面分

```text
0 ~ 20 分
```

### 风险分

```text
0 ~ -20 分
```

### 评级体系

```text
85 - 100：S
75 - 84：A
65 - 74：B
50 - 64：C
< 50：D
风险触发：R
```

## 本阶段使用的数据表

- daily_quote
- stock_basic
- factor_score
- strategy_signals

## 本阶段完成标志

```text
1. 每日可计算个股因子分
2. 每日可计算总分
3. 每日可生成评级
4. 可输出 Top 50、S、A、风险剔除列表
```

## 交付物

```text
每天收盘后生成：
- Top 50 股票
- S 级股票
- A 级股票
- 风险剔除股票
```

## 与下一阶段衔接

Phase 2 会在现有评分结果之上，增加市场状态约束和题材拥挤度调整，避免系统在环境不合适时盲目开仓。
