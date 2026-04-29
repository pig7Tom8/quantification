# Phase 5：策略快照与飞书推送

## 阶段目标

让系统每天自动复盘并推送，将当日市场状态、选股结果、虚拟账户表现和基准对比沉淀成固定日报。

## 对应原方案内容

- strategy_daily_snapshot
- 推送模块
- MVP 技术架构中的飞书机器人 Webhook 与 Markdown / CSV 报告
- Phase 5：strategy_daily_snapshot + 飞书推送，1 周
- MVP 最小闭环

## 本阶段范围

```text
- 写入 strategy_daily_snapshot
- 生成 Markdown 日报
- 生成 CSV 数据
- 接入飞书机器人
- 每日收盘后自动推送
```

## strategy_daily_snapshot 的作用

```text
1. 快速画收益曲线
2. 快速回看某天为什么选这些股票
3. 不用反复重算历史结果
4. 方便对比不同策略表现
5. 方便后期做策略淘汰和优化
```

## 日报建议内容

```text
1. 今日市场状态：进攻 / 震荡 / 防守
2. 市场状态原因
3. 今日 S / A 级股票数量
4. 今日 Top 10 选股
5. 每只股票入选原因
6. 题材拥挤度提醒
7. 重大资讯摘要
8. 虚拟账户收益
9. 基准账户收益
10. 超额收益
11. 最大回撤
12. 今日调仓动作
13. 明日观察清单
14. 风险提醒
```

## 需要落地的模块

```text
backend/
- snapshot/strategy_snapshot.py
- notification/feishu_push_service.py
- reports/daily_report.py
```

## 本阶段使用的数据表

- strategy_daily_snapshot
- factor_score
- news_events
- market_state_daily
- concept_crowding_daily
- virtual_positions

## 推送策略

```text
MVP 阶段只使用：飞书机器人
MVP 阶段只做：每日 1 次收盘推送
推送时间：15:30 ~ 18:00
```

## 本阶段完成标志

```text
1. 每日策略结果可写入 strategy_daily_snapshot
2. Markdown / CSV 日报可自动生成
3. 飞书机器人可自动收到收盘日报
4. 日报包含市场、评分、资讯、账户、基准、风险信息
```

## 交付物

```text
每天飞书收到完整收盘日报。
```

## 阶段完成后的整体能力

```text
1. 自动发现机会
2. 自动评分评级
3. 自动判断市场环境
4. 自动识别过热题材
5. 自动验证策略有效性
6. 自动记录每日策略快照
7. 自动推送复盘日报
```
