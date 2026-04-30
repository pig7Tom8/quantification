# Phase 2 市场状态与拥挤度测试用例

依据主 PRD `股票量化系统_MVP修订版方案.md`，本阶段只验收市场状态与题材拥挤度，不提前实现 Phase 3 资讯分。

## 验收点

```text
1. 系统可判断市场是进攻、震荡还是防守
2. 评级结果可受 market_state 约束
3. 系统可识别高拥挤和极高拥挤题材
4. 评级和开仓规则可受拥挤度调整
```

## 用例 1：市场状态落库

前置条件：

```text
已完成股票池、日 K、因子评分数据采集。
```

执行：

```bash
python3 tests/phase2_acceptance.py
```

预期：

```text
market_state_daily 当日有且只有 1 条记录
market_state ∈ 进攻 / 震荡 / 防守
up_count / down_count / total_amount / reason 有有效值
```

## 用例 2：题材拥挤度落库

预期：

```text
concept_crowding_daily 当日存在记录
crowding_level ∈ 低拥挤 / 中拥挤 / 高拥挤 / 极高拥挤
amount_ratio > 0
```

## 用例 3：拥挤度影响评分

预期：

```text
高拥挤或极高拥挤题材股票的 crowding_adjustment < 0
factor_score.reason 中说明对应题材拥挤度
```

## 用例 4：拥挤度影响评级

预期：

```text
高拥挤：
S → A
A → B

极高拥挤：
S / A 不直接降级，但不触发买入，只进入观察池
```

## 用例 5：市场状态影响开仓约束

预期：

```text
进攻：S / A 可参与虚拟买入，总仓位上限 100%
震荡：S 可虚拟买入，A 只观察，总仓位上限 60%
防守：所有评级只观察，不开新仓，总仓位上限 0% ~ 30%
```

对应结果写入 `strategy_signals.reason`。

## 用例 6：日报输出

预期：

```text
factor_report_YYYY-MM-DD.md 包含：
- 今日市场状态
- 市场状态原因
- 题材拥挤度提醒
- Top 50
- S 级股票
- A 级股票
- 风险剔除股票
```
