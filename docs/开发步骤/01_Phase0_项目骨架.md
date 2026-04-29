# Phase 0：项目骨架

## 阶段目标

搭好基础框架，让系统具备每天自动更新股票基础数据和行情数据的能力，并生成第一份本地 Markdown 日报。

## 对应原方案内容

- 总体架构
- 股票池管理
- 数据源设计
- 数据库设计
- MVP 技术架构
- MVP 项目结构
- Phase 0：项目骨架，1 周

## 本阶段范围

```text
- 明确股票市场范围
- 确定数据源
- 建数据库表
- 搭定时任务
- 拉取 A 股基础数据
- 拉取日 K 数据
- 生成第一份本地 Markdown 日报
```

## 关键约束

```text
- MVP 阶段先做日线数据，不做分钟级
- 股票池覆盖沪深主板、创业板、科创板
- 剔除 ST / *ST、退市风险、长期停牌、新股、低流动性股票
```

## 需要落地的模块

```text
backend/
- config.py
- scheduler.py
- data_collectors/quote_collector.py
- data_collectors/fundamental_collector.py
- reports/daily_report.py
```

## 优先建设的数据表

- stock_basic
- daily_quote

可一并预建但暂不完全使用：

- factor_score
- news_events
- virtual_positions
- strategy_signals
- market_state_daily
- concept_crowding_daily
- strategy_daily_snapshot

## 本阶段完成标志

```text
1. 每日调度可运行
2. 股票基础信息可入库
3. 日 K 行情可入库
4. 股票池过滤规则可执行
5. 本地 Markdown 日报可生成
```

## 交付物

```text
能每天自动更新股票基础数据和行情数据。
```

## 与下一阶段衔接

Phase 1 将基于本阶段落好的股票池、行情和财务数据，开始计算趋势分、资金分、基本面分、风险分和综合评分。
