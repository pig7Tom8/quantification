# Agent 输入输出关系表

## 目的

在不进入正式开发的前提下，补充说明各职责 Agent 之间的数据流转关系，明确谁依赖谁、谁产出什么、每个阶段应关注哪些输入输出。

---

## 1. 总体关系

推荐的 MVP 执行链路如下：

```text
DataAgent
→ NewsAgent
→ MarketAgent
→ ScoringAgent
→ StrategyAgent
→ PaperTradeAgent
→ ReportAgent
```

说明：

```text
- 这是确定性流程链
- 不代表必须使用多 Agent 框架
- 本质上是模块间输入输出依赖图
```

---

## 2. Agent 总览表

| Agent | 主要职责 | 主要输入 | 主要输出 | 下游使用方 |
|---|---|---|---|---|
| DataAgent | 采集并清洗基础数据 | 外部数据源 | 股票基础数据、行情数据、财务数据、原始资讯 | NewsAgent、MarketAgent、ScoringAgent |
| NewsAgent | 解析资讯并结构化 | 原始公告、新闻文本 | 结构化资讯事件、资讯摘要、置信度 | ScoringAgent、ReportAgent |
| MarketAgent | 判断市场状态与拥挤度 | 全市场行情、板块数据、强势股表现 | `market_state`、拥挤度结果 | ScoringAgent、StrategyAgent、PaperTradeAgent、ReportAgent |
| ScoringAgent | 计算各因子分与评级 | 行情、财务、资讯、市场状态、拥挤度 | 总分、评级、入选理由 | StrategyAgent、PaperTradeAgent、ReportAgent |
| StrategyAgent | 生成策略信号和风险剔除结果 | 评分结果、市场状态、拥挤度 | 策略信号、候选股票列表 | PaperTradeAgent、ReportAgent |
| PaperTradeAgent | 执行虚拟跑盘与基准对比 | 策略信号、评分、市场状态、行情 | 持仓结果、收益、回撤、超额收益 | ReportAgent |
| ReportAgent | 汇总并生成日报 | 市场、评分、资讯、交易、快照 | Markdown 日报、CSV、飞书推送内容 | 最终用户 |

---

## 3. 各 Agent 输入输出明细

### 3.1 DataAgent

#### 职责

```text
- 拉取股票基础信息
- 拉取日 K 行情
- 拉取财务数据
- 拉取公告和新闻原文
- 做基础清洗并入库
```

#### 主要输入

```text
- AkShare / Tushare / 东方财富等行情数据源
- 财务数据源
- 公告与新闻源
- 股票池配置
```

#### 主要输出

```text
- stock_basic
- daily_quote
- 财务原始数据或整理结果
- 原始公告 / 新闻文本
```

#### 直接下游

```text
- NewsAgent 读取原始资讯
- MarketAgent 读取全市场行情
- ScoringAgent 读取行情与财务数据
```

#### 失败影响

```text
- 数据缺失会导致后续评分、资讯、市场判断全部不稳定
- 因此是整条链路的上游基础模块
```

---

### 3.2 NewsAgent

#### 职责

```text
- 清洗公告和新闻文本
- 调用 LLM 提取结构化事件
- 生成摘要、方向、置信度
- 输出资讯事件结果
```

#### 主要输入

```text
- DataAgent 输出的原始公告 / 新闻文本
- LLM Prompt 模板
- 事件类型映射规则
```

#### 主要输出

```text
- news_events
- 资讯摘要
- 事件类型
- sentiment
- confidence
- news_score 的基础字段
```

#### 直接下游

```text
- ScoringAgent 用于计算 NewsScore
- ReportAgent 用于展示摘要和重大资讯
```

#### 失败影响

```text
- 不会阻塞纯行情评分
- 但会让“为什么入选”的解释能力下降
- 也会削弱资讯分有效性
```

---

### 3.3 MarketAgent

#### 职责

```text
- 判断当日 market_state
- 判断系统性风险
- 判断题材拥挤度
- 给评分和仓位提供环境限制
```

#### 主要输入

```text
- 全市场涨跌家数
- 全市场成交额
- 主要指数走势
- 涨停 / 跌停数据
- 热点板块数据
- 强势股表现
```

#### 主要输出

```text
- market_state_daily
- concept_crowding_daily
- 当日风险环境说明
```

#### 直接下游

```text
- ScoringAgent 用于评级约束
- StrategyAgent 用于信号过滤
- PaperTradeAgent 用于仓位控制
- ReportAgent 用于日报说明
```

#### 失败影响

```text
- 评分结果可能仍可运行
- 但无法正确约束开仓环境
- 容易在弱市或高拥挤环境下误触发策略
```

---

### 3.4 ScoringAgent

#### 职责

```text
- 计算趋势分
- 计算资金分
- 计算基本面分
- 计算资讯分
- 计算风险分
- 汇总总分并生成评级
```

#### 主要输入

```text
- daily_quote
- 财务整理结果
- news_events
- market_state
- crowding 信息
```

#### 主要输出

```text
- factor_score
- rating
- 入选理由
- 可供策略使用的候选股票集
```

#### 直接下游

```text
- StrategyAgent 用于策略筛选
- PaperTradeAgent 用于调仓参考
- ReportAgent 用于展示评级结果
```

#### 失败影响

```text
- 没有评分结果，系统无法进入选股、交易、日报主流程
- 属于 MVP 核心中枢模块
```

---

### 3.5 StrategyAgent

#### 职责

```text
- 依据评分和规则生成策略信号
- 输出趋势强势、低位启动、业绩共振等结果
- 对风险票进行降级或剔除
```

#### 主要输入

```text
- factor_score
- market_state
- crowding 信息
- 策略规则配置
```

#### 主要输出

```text
- strategy_signals
- 策略候选池
- 风险剔除列表
```

#### 直接下游

```text
- PaperTradeAgent 用于执行虚拟买卖
- ReportAgent 用于展示每日入选结果
```

#### 失败影响

```text
- 评分存在但无法落到具体策略动作
- 会使系统停留在“有分数、无执行信号”的状态
```

---

### 3.6 PaperTradeAgent

#### 职责

```text
- 执行虚拟买入
- 执行虚拟卖出
- 管理持仓与仓位
- 更新策略账户与基准账户
- 计算收益和风险指标
```

#### 主要输入

```text
- strategy_signals
- factor_score
- market_state
- 次日开盘价 / 行情数据
- 仓位控制规则
```

#### 主要输出

```text
- virtual_positions
- 策略账户收益
- 基准账户收益
- 超额收益
- 最大回撤
- 胜率
- 盈亏比
```

#### 直接下游

```text
- ReportAgent 用于汇总日报
- strategy_daily_snapshot 用于记录策略表现
```

#### 失败影响

```text
- 选股能做，但无法验证策略是否真正有效
- 会丢失 MVP 里最重要的“验证闭环”
```

---

### 3.7 ReportAgent

#### 职责

```text
- 汇总市场状态
- 汇总评分和策略结果
- 汇总资讯摘要
- 汇总虚拟账户与基准对比
- 生成 Markdown / CSV 日报
- 组织飞书推送内容
```

#### 主要输入

```text
- market_state_daily
- concept_crowding_daily
- factor_score
- news_events
- strategy_signals
- virtual_positions
- strategy_daily_snapshot
```

#### 主要输出

```text
- Markdown 日报
- CSV 报表
- 飞书推送文案
```

#### 直接下游

```text
- 最终用户
```

#### 失败影响

```text
- 策略与验证可能已运行
- 但无法稳定输出给用户复盘和决策使用
```

---

## 4. 阶段视角下的 Agent 参与关系

### Phase 0：项目骨架

主要涉及：

```text
- DataAgent
- ReportAgent（仅本地 Markdown 骨架）
```

目标：

```text
先把数据、表结构、调度、基础报告骨架跑通
```

---

### Phase 1：因子评分

主要涉及：

```text
- DataAgent
- ScoringAgent
- StrategyAgent（轻度参与）
```

目标：

```text
先让系统具备评分和评级能力
```

---

### Phase 2：市场状态与拥挤度

主要涉及：

```text
- MarketAgent
- ScoringAgent
- StrategyAgent
```

目标：

```text
给评分和开仓动作增加环境约束
```

---

### Phase 3：资讯抓取与 LLM 结构化

主要涉及：

```text
- DataAgent
- NewsAgent
- ScoringAgent
- ReportAgent
```

目标：

```text
让系统具备事件理解和解释能力
```

---

### Phase 4：虚拟跑盘与基准对比

主要涉及：

```text
- StrategyAgent
- PaperTradeAgent
```

目标：

```text
验证策略是否跑赢基准且回撤可控
```

---

### Phase 5：策略快照与飞书推送

主要涉及：

```text
- ReportAgent
- PaperTradeAgent
- MarketAgent
- NewsAgent
- ScoringAgent
```

目标：

```text
将全链路结果沉淀成日报和策略快照
```

---

## 5. 推荐的数据流顺序

```text
1. DataAgent 更新基础数据
2. NewsAgent 结构化资讯
3. MarketAgent 判断环境
4. ScoringAgent 计算总分和评级
5. StrategyAgent 生成策略信号
6. PaperTradeAgent 模拟执行并更新收益
7. ReportAgent 输出日报和推送内容
```

---

## 6. 当前建议

在正式开发前，只需要先把这些 Agent 当作：

```text
模块职责定义
```

不需要把它们实现成真正自治的智能体系统。

一句话结论：

> 先用 Agent 角色明确模块边界，再用普通工程方式实现，是当前 MVP 最稳的路线。
