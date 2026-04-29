# LLM 与 Agent 角色设计

## 目的

在不改变《股票量化系统 MVP 修订版方案》的前提下，补充说明本项目在 MVP 阶段对 LLM 和 Agent 的使用方式，明确模型边界、职责划分和后续扩展路径。

---

## 1. 结论

对于当前 MVP，建议采用：

```text
一个 LLM 即可
+ 多套 Prompt
+ 明确模块职责
+ 不引入复杂多 Agent 自治编排
```

也就是说：

- MVP 阶段先接入一个 LLM 即可
- 不同任务通过不同 Prompt 和输出 Schema 区分
- 业务流程仍由程序和规则引擎控制
- 不让 LLM 直接决定买卖
- 不急着上多智能体系统

---

## 2. 为什么 MVP 阶段一个 LLM 就够

当前方案里，LLM 的核心任务主要集中在资讯处理侧：

```text
1. 提取关键词
2. 识别事件类型
3. 识别影响对象
4. 判断正面 / 中性 / 负面
5. 输出置信度
6. 生成一句话摘要
```

这些任务本质上都属于：

```text
把非结构化文本转成结构化信息
```

因此 MVP 阶段没有必要一开始就引入多个模型。

推荐做法：

```text
一个 LLM Provider
一个统一调用层
多个任务级 Prompt
多个结构化输出格式
```

这样可以降低：

- 接入复杂度
- 调试复杂度
- 成本管理复杂度
- 后续维护成本

---

## 3. LLM 在 MVP 中的职责边界

### 3.1 LLM 负责的内容

```text
- 公告 / 新闻文本理解
- 事件类型识别
- 情绪方向判断
- 关键信息提取
- 一句话摘要生成
- 输出结构化结果
```

### 3.2 LLM 不负责的内容

```text
- 不直接决定是否买入
- 不直接决定是否卖出
- 不直接决定最终评分
- 不直接决定最终评级
- 不直接控制仓位
- 不直接触发交易动作
```

### 3.3 真正负责决策的模块

```text
- 规则引擎负责打分
- 评分引擎负责综合评分与评级
- 市场状态模块负责环境判断
- 拥挤度模块负责过热题材过滤
- 虚拟跑盘模块负责买卖模拟和仓位控制
```

换句话说：

```text
LLM 负责“理解文本”
规则系统负责“做决策”
```

---

## 4. 推荐的 LLM 使用方式

### 4.1 技术策略

推荐采用单模型、多任务路由的方式。

```text
llm_client
├── news_extractor
├── sentiment_classifier
├── summary_generator
└── future_research_analyst
```

实现层面可以仍然共用同一个底层模型，只是在业务上拆成不同用途。

### 4.2 MVP 阶段建议保留的任务入口

#### news_extractor

用途：

```text
从公告、新闻、互动问答中提取结构化事件
```

输出建议：

```json
{
  "stock_codes": ["600000"],
  "event_type": "订单合同",
  "sentiment": "positive",
  "confidence": 0.92,
  "keywords": ["订单", "中标", "算力"],
  "summary": "公司披露新订单，事件偏正面。"
}
```

#### sentiment_classifier

用途：

```text
对事件方向进行辅助判断
```

说明：

```text
该能力也可以合并进 news_extractor，一开始不强制拆开。
```

#### summary_generator

用途：

```text
为日报生成简洁摘要或市场解释文本
```

说明：

```text
MVP 阶段可以复用同一个 LLM，不需要单独换模型。
```

---

## 5. 是否需要额外定义 Agent

需要定义职责，但不建议在 MVP 阶段上复杂多 Agent 系统。

这里要区分两件事：

### 5.1 需要定义的是“职责 Agent”

也就是：

```text
谁负责什么模块
谁消费什么数据
谁输出什么结果
```

这个非常有必要，因为它能帮助我们：

- 拆目录结构
- 拆开发任务
- 设计测试用例
- 降低模块耦合
- 方便后期替换实现

### 5.2 暂时不需要的是“自治多 Agent 编排系统”

也就是不建议现在做这种复杂形态：

```text
多个 AI Agent 自动互相讨论
自动分工
自动协商
自动决定任务流转
```

原因：

```text
- MVP 阶段没必要
- 调试困难
- 可控性差
- 出错定位困难
- 会明显增加系统复杂度
```

结论：

```text
先定义模块角色
先做确定性流程
后续再决定是否升级为真正多 Agent
```

---

## 6. MVP 推荐的 Agent 角色划分

以下 Agent 更适合理解为“模块责任角色”，不一定意味着必须使用智能体框架。

### 6.1 DataAgent

职责：

```text
- 拉取股票基础信息
- 拉取日 K 行情
- 拉取财务数据
- 拉取公告和新闻原文
- 清洗原始数据并写库
```

输入：

```text
外部数据源
```

输出：

```text
stock_basic
daily_quote
原始资讯数据
```

---

### 6.2 NewsAgent

职责：

```text
- 调用 LLM 解析公告和新闻
- 提取事件类型、方向、对象、置信度
- 生成一句话摘要
- 产出可供规则引擎使用的结构化事件
```

输入：

```text
原始公告 / 新闻文本
```

输出：

```text
news_events
news_score 的基础数据
```

---

### 6.3 MarketAgent

职责：

```text
- 判断 market_state
- 判断系统性风险
- 判断题材拥挤度
- 给评分和开仓动作提供环境约束
```

输入：

```text
全市场行情
板块数据
强势股表现
```

输出：

```text
market_state_daily
concept_crowding_daily
```

---

### 6.4 ScoringAgent

职责：

```text
- 计算趋势分
- 计算资金分
- 计算基本面分
- 计算资讯分
- 计算风险分
- 汇总总分并生成评级
```

输入：

```text
daily_quote
财务数据
news_events
market_state
crowding 信息
```

输出：

```text
factor_score
股票评级
策略候选列表
```

---

### 6.5 StrategyAgent

职责：

```text
- 根据评级和规则生成策略信号
- 输出趋势强势、低位启动、业绩共振等候选结果
- 风险票降级或剔除
```

输入：

```text
factor_score
market_state
crowding 信息
```

输出：

```text
strategy_signals
```

---

### 6.6 PaperTradeAgent

职责：

```text
- 执行虚拟买入
- 执行虚拟卖出
- 管理虚拟仓位
- 更新策略账户与基准账户收益
- 计算超额收益、回撤、胜率、盈亏比
```

输入：

```text
strategy_signals
factor_score
market_state
```

输出：

```text
virtual_positions
策略收益指标
基准收益指标
```

---

### 6.7 ReportAgent

职责：

```text
- 汇总市场状态
- 汇总选股与评分结果
- 汇总资讯摘要
- 汇总账户表现与基准对比
- 生成 Markdown / CSV 日报
- 推送飞书日报
```

输入：

```text
market_state_daily
factor_score
news_events
virtual_positions
strategy_daily_snapshot
```

输出：

```text
Markdown 日报
CSV 报表
飞书推送内容
```

---

## 7. 推荐的执行关系

MVP 阶段推荐的执行链路如下：

```text
DataAgent
→ NewsAgent
→ MarketAgent
→ ScoringAgent
→ StrategyAgent
→ PaperTradeAgent
→ ReportAgent
```

这是一条：

```text
确定性流程链
```

而不是：

```text
多个 Agent 自由协商的自治系统
```

---

## 8. 代码层面的建议

为了后续可扩展，建议现在就在代码结构上按“角色职责”拆模块，而不是把所有逻辑堆在一起。

建议与原方案目录保持一致：

```text
backend/
├── data_collectors/
├── factors/
├── strategies/
├── scoring/
├── paper_trading/
├── snapshot/
├── notification/
└── reports/
```

如果后续要增强，可以新增：

```text
backend/llm/
├── client.py
├── prompts/
│   ├── news_extractor.md
│   ├── summary_generator.md
│   └── research_analyst.md
└── schemas/
    ├── news_event_schema.json
    └── report_summary_schema.json
```

这样做的好处：

```text
- 现在只接一个模型也不乱
- 以后换模型不影响业务层
- 以后拆多个模型也不需要重构主流程
- Prompt、Schema、调用逻辑可以分别测试
```

---

## 9. 什么时候再考虑多个 LLM

只有当出现以下情况时，再考虑拆多个模型：

```text
1. 资讯抽取与日报写作对模型要求差异明显
2. 成本压力上升
3. 结构化输出稳定性要求更高
4. 引入 AI 研究员模块后，需要更长链路分析
5. 不同任务在时延和质量上需要单独优化
```

那个时候可以演进为：

```text
- 结构化模型：负责 news extraction
- 总结模型：负责日报与复盘总结
- 研究模型：负责 AI 研究员与深度解释
```

但这不是当前 MVP 的必需项。

---

## 10. 当前建议

当前最适合本项目的方案是：

```text
1. 先接一个 LLM
2. 明确 LLM 只做资讯理解和结构化
3. 明确各模块 Agent 职责
4. 不做复杂多 Agent 编排
5. 保持后续可升级空间
```

一句话结论：

> MVP 阶段先做“单 LLM + 明确职责模块”的稳定系统，比一开始上复杂多模型、多 Agent 方案更适合这个项目。
