# LLM 调用接口与返回 Schema 草案

## 目的

在不进入正式开发的前提下，为后续 LLM 接入预先定义统一调用方式、任务入口和结构化返回格式，确保将来真正开发时，LLM 能稳定服务于资讯结构化和日报生成，而不是直接介入交易决策。

---

## 1. 设计原则

### 1.1 单 LLM，统一调用层

MVP 阶段建议采用：

```text
一个 LLM Provider
+ 一个统一 llm_client
+ 多个任务入口
+ 固定结构化输出 Schema
```

目的：

```text
- 降低接入复杂度
- 降低 Prompt 分散带来的维护成本
- 方便后续替换模型
- 方便单独测试每个任务入口
```

### 1.2 LLM 只负责理解，不负责决策

LLM 只做：

```text
- 文本理解
- 信息提取
- 情绪判断
- 摘要生成
- 结构化输出
```

LLM 不做：

```text
- 买卖决策
- 最终评分
- 最终评级
- 仓位控制
- 风险开仓控制
```

---

## 2. 推荐目录草案

后续如果实现，可参考以下结构：

```text
backend/llm/
├── client.py
├── router.py
├── prompts/
│   ├── news_extractor.md
│   ├── summary_generator.md
│   └── research_analyst.md
└── schemas/
    ├── news_event_schema.json
    ├── report_summary_schema.json
    └── research_result_schema.json
```

说明：

```text
- client.py：统一封装底层模型调用
- router.py：按任务类型路由到不同 Prompt
- prompts/：维护任务 Prompt
- schemas/：维护结构化输出约束
```

---

## 3. 推荐任务入口

MVP 阶段建议优先保留以下 2 到 3 个任务入口。

### 3.1 `news_extractor`

用途：

```text
把公告、新闻、互动问答转成结构化事件
```

输入：

```text
原始资讯文本
```

输出：

```text
事件类型、方向、对象、关键词、置信度、摘要
```

是否必须：

```text
必须
```

---

### 3.2 `summary_generator`

用途：

```text
根据结构化结果生成日报中的简洁说明或一句话总结
```

输入：

```text
结构化资讯、市场状态、评分结果
```

输出：

```text
适合日报展示的短文本
```

是否必须：

```text
建议保留，但不是第一优先级
```

---

### 3.3 `research_analyst`

用途：

```text
用于后续 AI 研究员模块，对个股做更完整的解释
```

输入：

```text
股票代码、走势、财务、资讯、评分变化、市场状态、拥挤度
```

输出：

```text
一句话结论、上涨逻辑、风险点、适合短线还是中线、置信度
```

是否必须：

```text
MVP 阶段不是必须，可预留接口
```

---

## 4. 统一调用接口草案

### 4.1 抽象接口

后续调用层建议统一成类似形态：

```python
result = llm_client.run(
    task="news_extractor",
    input_data={...},
    output_schema={...},
)
```

建议参数：

```text
- task：任务名称
- input_data：业务输入内容
- output_schema：期望结构化返回格式
- metadata：可选，记录来源、股票代码、时间等上下文
```

---

### 4.2 接口示例

```python
result = llm_client.run(
    task="news_extractor",
    input_data={
        "source": "巨潮资讯",
        "title": "某公司中标重大项目公告",
        "content": "......"
    },
    output_schema="news_event_schema"
)
```

预期含义：

```text
- 用 news_extractor 的 Prompt
- 按 news_event_schema 返回结构化结果
- 业务侧不关心底层具体模型细节
```

---

## 5. `news_extractor` 返回 Schema 草案

### 5.1 目标

把资讯原文统一转换成可入库、可打分、可复盘的结构化事件。

### 5.2 建议字段

```json
{
  "stock_codes": ["600000"],
  "stock_names": ["示例股份"],
  "event_type": "订单合同",
  "sentiment": "positive",
  "confidence": 0.92,
  "impact_level": "high",
  "keywords": ["订单", "中标", "算力"],
  "industry_tags": ["AI算力", "服务器"],
  "summary": "公司披露重大订单，中短期偏正面。",
  "reasoning_brief": "公告涉及新增订单，金额较大，事件偏正面。",
  "time_reference": "2026-04-29",
  "risk_flags": []
}
```

### 5.3 字段说明

| 字段 | 类型 | 含义 |
|---|---|---|
| `stock_codes` | list[string] | 涉及的股票代码，可多只 |
| `stock_names` | list[string] | 涉及的股票名称 |
| `event_type` | string | 事件类型 |
| `sentiment` | string | `positive` / `neutral` / `negative` |
| `confidence` | number | 0 到 1 的置信度 |
| `impact_level` | string | `low` / `medium` / `high` |
| `keywords` | list[string] | 抽取出的关键词 |
| `industry_tags` | list[string] | 行业 / 概念标签 |
| `summary` | string | 一句话摘要 |
| `reasoning_brief` | string | 简短解释，便于人工复核 |
| `time_reference` | string | 事件对应时间 |
| `risk_flags` | list[string] | 风险标记，如减持、监管问询等 |

### 5.4 设计说明

```text
- `summary` 用于日报展示
- `reasoning_brief` 用于人工检查和测试验证
- `risk_flags` 便于后续风险因子直接消费
- `confidence` 用于控制是否计分以及计分权重
```

---

## 6. `summary_generator` 返回 Schema 草案

### 6.1 目标

为日报、复盘或市场说明生成简洁、可读、可控的短文本。

### 6.2 建议字段

```json
{
  "title": "今日市场状态说明",
  "summary": "市场处于震荡，热点轮动较快，建议控制仓位。",
  "highlights": [
    "上涨家数略多于下跌家数",
    "成交额未明显放大",
    "高拥挤题材不宜追高"
  ],
  "risk_note": "市场仍未进入明确进攻阶段。"
}
```

### 6.3 使用场景

```text
- 飞书日报中的市场总结
- 某只股票的简明入选原因展示
- 风险提醒说明
```

---

## 7. `research_analyst` 返回 Schema 草案

### 7.1 目标

为后续 AI 研究员模块预留统一输出格式。

### 7.2 建议字段

```json
{
  "stock_code": "600000",
  "conclusion": "短线可观察，中线需等业绩确认。",
  "bullish_points": [
    "趋势保持完好",
    "板块资金活跃",
    "公告事件偏正面"
  ],
  "risk_points": [
    "题材拥挤度偏高",
    "短线涨幅已不低"
  ],
  "style_fit": "short_term",
  "confidence": 0.76,
  "summary": "逻辑存在，但更适合观察回踩后的机会。"
}
```

### 7.3 是否立即实现

```text
当前只建议保留文档草案，不建议立即进入正式开发。
```

---

## 8. 结构化输出的约束建议

为了提高稳定性，后续真正实现时建议遵守以下约束：

```text
1. 尽量要求 JSON 输出
2. 字段名固定
3. 枚举值固定
4. 缺失字段返回 null 或空数组
5. 不允许返回额外长篇自由文本替代结构化字段
```

推荐约束重点：

```text
- event_type 必须在预定义集合中
- sentiment 必须是 positive / neutral / negative
- confidence 必须是 0 ~ 1
- risk_flags 必须是数组
```

---

## 9. 错误处理建议

后续正式开发时，LLM 调用层建议预留以下异常处理方式：

### 9.1 输出格式不合法

处理建议：

```text
- 记录原始响应
- 触发一次重试
- 仍失败则标记为解析失败
- 不直接进入评分，只进入待复核或忽略队列
```

### 9.2 置信度过低

处理建议：

```text
- 不计入资讯分
- 保留摘要和事件结果供人工观察
```

### 9.3 事件类型无法判断

处理建议：

```text
- 归类为 unknown 或 other
- 不直接加分或减分
- 保留原始文本用于后续规则补充
```

---

## 10. 测试前置建议

虽然当前不进入正式开发，但后面进入实现时，LLM 接口测试建议至少覆盖：

```text
- 正常公告抽取
- 单条新闻抽取
- 一条资讯涉及多只股票
- 负面公告识别
- 模糊标题 / 噪声资讯处理
- 空文本输入
- 非法 JSON 输出重试
- 低置信度结果处理
```

---

## 11. 当前建议

当前阶段最适合的方式是：

```text
- 先把 LLM 调用入口和返回 Schema 在文档里定清楚
- 不急着落代码
- 不急着接多个模型
- 不让 LLM 直接碰交易决策
```

一句话结论：

> 先统一 LLM 的接口和结构化输出格式，后续开发时会比先写代码再返工稳得多。
