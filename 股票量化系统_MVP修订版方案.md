# 股票量化系统 MVP 修订版方案

> 版本：V2 修订版  
> 目标：做一个先能跑起来、能验证策略有效性、能通过飞书机器人每日推送的轻量级量化选股系统。  
> 核心原则：先验证策略，再考虑复杂功能；先做自动复盘和虚拟跑盘，不直接实盘自动交易。

---

## 0. 系统定位

本系统第一阶段不做全自动交易，也不做复杂前端平台，而是先做一个：

> **能自动选股、打分评级、抓资讯、虚拟跑盘、基准对比、每日推送，并持续验证策略有效性的个人量化决策系统。**

MVP 阶段重点解决 5 个问题：

```text
1. 今天市场适不适合进攻？
2. 哪些股票符合策略？
3. 它们为什么被选出来？
4. 策略是否真的跑赢基准？
5. 每天能否自动复盘并推送结果？
```

系统不追求一开始就预测每只股票涨跌，而是建立稳定流程：

```text
发现机会 → 量化评分 → 风险过滤 → 虚拟验证 → 基准对比 → 复盘优化
```

---

## 1. MVP 核心原则

### 1.1 做减法

MVP 阶段不做：

```text
- Vue / React 前端页面
- 实盘自动交易
- 高频交易
- 复杂机器学习
- 复杂 Web Dashboard
- 全市场分钟级实时扫描
- 多账户管理
```

MVP 阶段只做：

```text
- 股票池
- 行情采集
- 基础财务数据
- 资讯抓取
- LLM 资讯结构化
- 多因子评分
- 市场状态判断
- 题材拥挤度判断
- 策略信号生成
- 虚拟跑盘
- 基准对比
- strategy_daily_snapshot
- 飞书机器人推送
- Markdown / CSV 日报
```

---

## 2. 总体架构

```text
数据源
  ↓
行情 / 财务 / 资讯采集
  ↓
数据清洗与入库
  ↓
市场状态判断
  ↓
个股因子计算
  ↓
资讯事件结构化
  ↓
题材拥挤度判断
  ↓
综合评分与评级
  ↓
策略信号生成
  ↓
虚拟跑盘
  ↓
基准账户对比
  ↓
策略快照记录
  ↓
飞书机器人推送
```

---

## 3. 股票池管理

### 3.1 初始股票池

初始建议覆盖 A 股主要股票，但要做基础过滤。

```text
范围：
- 沪深主板
- 创业板
- 科创板

剔除：
- ST / *ST
- 退市风险股票
- 长期停牌股票
- 上市不足 120 个交易日的新股
- 近 20 日平均成交额低于 5000 万的股票
- 流动性明显不足的股票
```

### 3.2 股票池分类

```text
全市场股票池
├── 可交易股票池
│   ├── 趋势强势池
│   ├── 低位启动池
│   ├── 业绩增长池
│   ├── 题材活跃池
│   └── 风险观察池
```

---

## 4. 数据源设计

### 4.1 行情数据

优先考虑：

```text
- AkShare
- Tushare
- 东方财富接口
- 其他可用公开数据源
```

MVP 阶段先做日线数据，不做分钟级。

采集字段：

```text
股票代码
股票名称
交易日期
开盘价
最高价
最低价
收盘价
成交量
成交额
涨跌幅
换手率
总市值
流通市值
行业
概念
```

### 4.2 财务数据

MVP 只抓核心指标：

```text
营收同比增长
净利润同比增长
扣非净利润
ROE
毛利率
资产负债率
经营现金流
商誉
```

### 4.3 资讯数据

资讯因子是系统的重要模块，但题材范围应由配置文件动态维护，不应写死在系统设计中。

系统只负责识别：

```text
事件类型
影响方向
影响对象
影响强度
风险等级
置信度
```

建议资讯源：

```text
- 巨潮资讯
- 交易所公告
- 东方财富公告
- 财联社
- 证券时报
- 中国证券报
- 上海证券报
- 公司官网
- 互动易 / 上证 e 互动
- 雪球 / 股吧，低权重，仅做情绪参考
```

---

## 5. 市场状态因子

### 5.1 为什么需要市场状态

个股策略不能脱离市场环境。有些时候不是股票不好，而是市场处于系统性风险阶段。  
如果大盘环境很差，系统应该降低仓位甚至停止开新仓。

### 5.2 市场状态分类

```text
market_state = 进攻 / 震荡 / 防守
```

### 5.3 市场状态判断指标

```text
1. 全市场上涨 / 下跌家数比例
2. 全市场成交额变化
3. 主要指数趋势
4. 涨停家数
5. 跌停家数
6. 强势股补跌情况
7. 高位股亏钱效应
8. 市场连板高度
9. 热点板块持续性
```

### 5.4 市场状态规则示例

#### 进攻

```text
条件示例：
- 上涨家数明显多于下跌家数
- 全市场成交额放大
- 主要指数站上 MA20
- 涨停家数较多
- 强势板块有持续性
- 高位股未出现明显亏钱效应
```

动作：

```text
- 允许 S / A 级股票进入虚拟买入
- 单票仓位可按正常规则执行
- 总仓位上限 100%
```

#### 震荡

```text
条件示例：
- 上涨和下跌家数接近
- 成交额没有明显放大
- 指数围绕均线震荡
- 热点轮动较快
```

动作：

```text
- S 级股票可以虚拟买入
- A 级股票只进入观察池
- 总仓位上限 60%
- 更严格执行止损
```

#### 防守

```text
条件示例：
- 全市场下跌家数 > 70%
- 全市场成交额连续萎缩
- 主要指数跌破 MA20 / MA60
- 强势股补跌
- 跌停数量明显增加
- 热点板块持续性差
```

动作：

```text
- 不开新仓
- 只保留已有持仓观察
- 评分下降股票减仓或清仓
- 只推送观察清单，不触发虚拟买入
- 总仓位上限 0% ~ 30%
```

---

## 6. 因子体系

综合评分由以下部分组成：

```text
总分 = 趋势分 + 资金分 + 基本面分 + 资讯分 + 风险分 + 拥挤度调整
```

建议总分区间为 0 ~ 100。

---

## 7. 技术趋势因子

### 7.1 权重建议

```text
趋势分：0 ~ 30 分
```

### 7.2 加分规则

```text
+5  股价 > MA20
+5  MA5 > MA10 > MA20
+5  最近 20 日涨幅在 5% ~ 35%
+5  最近 10 日有放量阳线
+5  距离 60 日新高小于 5%
+5  最近回撤小于 15%
```

### 7.3 扣分规则

```text
-5   跌破 MA20
-5   最近 20 日涨幅 > 60%，短线过热
-5   最近 5 日放量下跌
-10  股价跌破 MA60
```

---

## 8. 资金强度因子

### 8.1 权重建议

```text
资金分：0 ~ 25 分
```

### 8.2 加分规则

```text
+5  近 5 日成交额持续放大
+5  今日成交额大于近 20 日均值 1.5 倍
+5  换手率在 3% ~ 15%
+5  近 3 日资金净流入为正
+5  所属板块成交额排名靠前
```

### 8.3 扣分规则

```text
-5  高位爆量长上影
-5  连续 3 日资金流出
-5  换手率过高，比如 > 30%
```

---

## 9. 基本面因子

### 9.1 权重建议

```text
基本面分：0 ~ 20 分
```

### 9.2 加分规则

```text
+5  营收同比增长 > 10%
+5  净利润同比增长 > 10%
+5  ROE > 8%
+3  毛利率稳定或提升
+2  资产负债率不过高
```

### 9.3 扣分规则

```text
-5  净利润连续下滑
-5  扣非净利润为负
-5  商誉占比过高
-5  资产负债率明显高于行业平均
```

---

## 10. 资讯因子

### 10.1 资讯因子的目标

资讯因子不是让大模型直接判断买卖，而是把非结构化资讯转成可计算事件。

```text
公告 / 新闻 / 互动问答
  ↓
LLM 结构化提取
  ↓
规则引擎打分
  ↓
进入综合评分
```

### 10.2 事件类型

```text
政策利好
产业趋势
订单合同
业绩预增
涨价逻辑
技术突破
机构调研
高管增持
回购
减持风险
监管问询
诉讼风险
澄清公告
业绩预亏
商誉减值
财务异常
```

### 10.3 LLM 的职责

LLM 只做结构化提取，不直接决定最终分数。

```text
LLM 负责：
1. 提取关键词
2. 识别事件类型
3. 提取涉及公司、行业、产品、金额、时间
4. 判断事件方向：正面 / 中性 / 负面
5. 输出置信度
6. 生成一句话摘要
```

### 10.4 LLM 不应该做的事

```text
LLM 不做：
- 不直接判断是否买入
- 不直接判断是否卖出
- 不直接决定最终评分
- 不直接生成 0/1 决策
```

### 10.5 资讯评分规则

最终资讯分由硬编码规则计算。

```text
资讯分：-15 ~ +15
```

示例规则：

```text
业绩预增：+3
订单合同：+3
回购增持：+2
政策支持：+3
行业涨价：+3
机构调研热度上升：+2

减持：-5
监管问询：-3
诉讼风险：-3
业绩预亏：-5
商誉减值：-5
澄清公告：-2
财务异常：-8
```

### 10.6 置信度处理

```text
高置信度：正常计分
中置信度：分数 * 0.5
低置信度：不计入评分，只进入观察
```

---

## 11. 风险因子

### 11.1 个股风险

```text
风险分：0 ~ -20
```

扣分规则：

```text
-5   ST / 退市风险
-5   近 20 日涨幅过高且无业绩支撑
-5   大股东减持
-5   连续跌破关键均线
-5   业绩亏损扩大
-5   换手率异常过高
-10  监管处罚 / 财务造假风险
```

### 11.2 系统性风险

系统性风险不直接属于某只股票，而是影响整个策略是否应该开仓。

系统性风险包括：

```text
全市场下跌家数 > 70%
全市场成交额连续萎缩
强势股补跌
高位股集体杀跌
主要指数跌破关键均线
跌停家数明显增加
热点板块持续性下降
```

系统性风险通过 `market_state` 控制仓位和开仓权限。

---

## 12. 题材拥挤度判断

### 12.1 为什么需要拥挤度

很多股票看起来逻辑很好，但买进去就亏，原因可能不是逻辑错了，而是市场已经过度交易。

系统需要判断：

```text
这个题材是否已经太热？
是否已经人尽皆知？
是否出现高位接力风险？
```

### 12.2 拥挤度指标

MVP 做轻量版即可。

```text
题材拥挤度 =
- 该概念板块成交额 / 全市场成交额
- 该概念板块涨停家数占比
- 该概念板块 RSI > 70 的个股比例
- 该概念板块近 5 日平均涨幅
- 该概念板块高位股是否开始补跌
```

### 12.3 拥挤度分级

```text
低拥挤：可以正常参与
中拥挤：降低评级或降低仓位
高拥挤：禁止追高，只观察
极高拥挤：不新开仓，已有持仓加强止盈
```

### 12.4 拥挤度对评级的影响

```text
高拥挤：
- S → A
- A → B / 观察
- 禁止虚拟追高买入

极高拥挤：
- S / A 均不触发买入
- 只进入观察池
```

---

## 13. 综合评分与评级

### 13.1 总分公式

```text
Score = TrendScore
      + MoneyScore
      + FundamentalScore
      + NewsScore
      + RiskScore
      + CrowdingAdjustment
```

### 13.2 评级体系

| 分数 | 评级 | 含义 | 操作建议 |
|---:|---|---|---|
| 85 - 100 | S | 强趋势 + 强资金 + 强题材 | 重点观察 / 虚拟买入 |
| 75 - 84 | A | 有较强机会 | 加入核心观察池 |
| 65 - 74 | B | 有潜力但确认不足 | 观察 |
| 50 - 64 | C | 普通 | 不操作 |
| < 50 | D | 弱势或风险较大 | 剔除 |
| 风险触发 | R | 风险票 | 禁止买入 |

### 13.3 评级受市场状态约束

```text
市场进攻：
- S / A 可参与虚拟买入

市场震荡：
- S 可虚拟买入
- A 只观察

市场防守：
- 所有评级只观察
- 不开新仓
```

---

## 14. 策略设计

MVP 第一版建议只做 4 个策略。

### 14.1 趋势强势策略

适合寻找趋势已经形成的强势股。

入选条件：

```text
- 股价 > MA20
- MA5 > MA10 > MA20
- 近 20 日涨幅 5% ~ 40%
- 近 5 日成交额放大
- 所属板块强度排名靠前
- 无重大负面公告
- 拥挤度不能为极高
```

### 14.2 低位放量启动策略

适合寻找刚启动的题材股。

入选条件：

```text
- 近 60 日涨幅 < 30%
- 今日涨幅 > 3%
- 今日成交额 > 近 20 日均值 2 倍
- 股价突破 MA20
- 有资讯或板块催化
- 非高拥挤题材
```

### 14.3 业绩 + 资金共振策略

适合中线观察。

入选条件：

```text
- 营收同比增长 > 10%
- 净利润同比增长 > 10%
- ROE > 8%
- 股价趋势不破 MA60
- 近 20 日资金净流入为正
```

### 14.4 风险剔除策略

该策略不是选股，而是过滤和降级。

触发条件：

```text
- ST / 退市风险
- 重大负面公告
- 业绩预亏
- 减持压力大
- 监管问询
- 财务异常
- 放量破位
- 市场状态进入防守
```

动作：

```text
- 降级
- 禁止买入
- 已持仓则触发减仓或清仓规则
```

---

## 15. 策略有效性验证机制

### 15.1 为什么需要验证机制

虚拟跑盘只能说明系统有没有赚钱，但不能说明策略是否有效。

如果市场整体大涨，很多策略都会赚钱。  
所以必须看：

```text
是否跑赢基准？
是否跑赢无脑追涨？
是否在弱市少亏？
收益来源是否稳定？
```

### 15.2 虚拟账户设计

```text
虚拟账户 A：本系统策略账户
虚拟账户 B：指数基准账户，例如沪深 300 / 中证 500
虚拟账户 C：全市场等权基准账户
```

### 15.3 对比指标

```text
1. 策略收益率
2. 基准收益率
3. 超额收益率
4. 最大回撤
5. 胜率
6. 盈亏比
7. 平均持仓天数
8. 收益波动率
9. 防守市场下的亏损控制能力
```

### 15.4 核心判断

```text
策略有效 ≠ 赚钱
策略有效 = 长期稳定跑赢合理基准，并且回撤可控
```

---

## 16. 虚拟跑盘模块

### 16.1 初始账户规则

```text
初始资金：1000000
单票最大仓位：10%
单行业最大仓位：30%
最大持仓数量：10 只
单票最大亏损：-8%
组合最大回撤：-15%
```

### 16.2 开仓规则

#### 市场进攻

```text
S 级股票：
- 次日开盘虚拟买入
- 仓位 8% ~ 10%

A 级股票：
- 次日开盘虚拟买入
- 仓位 5%
```

#### 市场震荡

```text
S 级股票：
- 次日开盘虚拟买入
- 仓位 5%

A 级股票：
- 不买入，只观察
```

#### 市场防守

```text
- 不开新仓
- 只推送观察
```

### 16.3 卖出规则

```text
止损：
- 跌破买入价 8%
- 或跌破 MA20
- 或出现重大负面资讯

止盈：
- 盈利 15% 后上移止损
- 盈利 25% 后减半
- 趋势未破则保留底仓

调仓：
- 评分跌破 65，减仓
- 评分跌破 55，清仓
- 出现 R 级风险，清仓
- 市场状态转防守，降低总仓位
```

---

## 17. 数据库设计

推荐 PostgreSQL。  
如果 MVP 想更轻，也可以先 SQLite，后续再迁移 PostgreSQL。

### 17.1 stock_basic

```sql
CREATE TABLE stock_basic (
    stock_code VARCHAR(20) PRIMARY KEY,
    stock_name VARCHAR(100),
    exchange VARCHAR(20),
    industry VARCHAR(100),
    concepts TEXT,
    market_cap NUMERIC,
    is_st BOOLEAN,
    list_date DATE,
    status VARCHAR(50),
    updated_at TIMESTAMP
);
```

### 17.2 daily_quote

```sql
CREATE TABLE daily_quote (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(20),
    trade_date DATE,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume NUMERIC,
    amount NUMERIC,
    turnover_rate NUMERIC,
    pct_chg NUMERIC,
    ma5 NUMERIC,
    ma10 NUMERIC,
    ma20 NUMERIC,
    ma60 NUMERIC,
    created_at TIMESTAMP
);
```

### 17.3 factor_score

```sql
CREATE TABLE factor_score (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(20),
    trade_date DATE,
    trend_score NUMERIC,
    money_score NUMERIC,
    fundamental_score NUMERIC,
    news_score NUMERIC,
    risk_score NUMERIC,
    crowding_adjustment NUMERIC,
    total_score NUMERIC,
    rating VARCHAR(10),
    reason TEXT,
    created_at TIMESTAMP
);
```

### 17.4 news_events

```sql
CREATE TABLE news_events (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(20),
    publish_time TIMESTAMP,
    source VARCHAR(100),
    title TEXT,
    summary TEXT,
    event_type VARCHAR(100),
    sentiment VARCHAR(20),
    confidence NUMERIC,
    impact_score NUMERIC,
    url TEXT,
    created_at TIMESTAMP
);
```

### 17.5 virtual_positions

```sql
CREATE TABLE virtual_positions (
    id SERIAL PRIMARY KEY,
    account_name VARCHAR(100),
    stock_code VARCHAR(20),
    buy_date DATE,
    buy_price NUMERIC,
    position_pct NUMERIC,
    shares NUMERIC,
    current_price NUMERIC,
    pnl NUMERIC,
    pnl_pct NUMERIC,
    status VARCHAR(50),
    sell_date DATE,
    sell_price NUMERIC,
    sell_reason TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 17.6 strategy_signals

```sql
CREATE TABLE strategy_signals (
    id SERIAL PRIMARY KEY,
    trade_date DATE,
    stock_code VARCHAR(20),
    strategy_name VARCHAR(100),
    signal_type VARCHAR(50),
    score NUMERIC,
    rating VARCHAR(10),
    reason TEXT,
    created_at TIMESTAMP
);
```

### 17.7 market_state_daily

```sql
CREATE TABLE market_state_daily (
    id SERIAL PRIMARY KEY,
    trade_date DATE,
    market_state VARCHAR(20),
    up_count INTEGER,
    down_count INTEGER,
    limit_up_count INTEGER,
    limit_down_count INTEGER,
    total_amount NUMERIC,
    index_trend TEXT,
    strong_stock_status TEXT,
    reason TEXT,
    created_at TIMESTAMP
);
```

### 17.8 concept_crowding_daily

```sql
CREATE TABLE concept_crowding_daily (
    id SERIAL PRIMARY KEY,
    trade_date DATE,
    concept_name VARCHAR(100),
    concept_amount NUMERIC,
    market_amount NUMERIC,
    amount_ratio NUMERIC,
    limit_up_count INTEGER,
    rsi_over_70_ratio NUMERIC,
    avg_5d_return NUMERIC,
    crowding_level VARCHAR(20),
    created_at TIMESTAMP
);
```

### 17.9 strategy_daily_snapshot

这张表是 MVP 必须增加的表，用来记录每天策略表现，方便后续复盘和画收益曲线。

```sql
CREATE TABLE strategy_daily_snapshot (
    id SERIAL PRIMARY KEY,
    trade_date DATE,
    strategy_name VARCHAR(100),
    market_state VARCHAR(20),
    selected_count INTEGER,
    s_count INTEGER,
    a_count INTEGER,
    hold_count INTEGER,
    top5_stocks TEXT,
    top5_scores TEXT,
    paper_pnl NUMERIC,
    paper_total_return NUMERIC,
    paper_max_drawdown NUMERIC,
    benchmark_name VARCHAR(100),
    benchmark_return NUMERIC,
    excess_return NUMERIC,
    win_rate NUMERIC,
    avg_holding_days NUMERIC,
    reason TEXT,
    created_at TIMESTAMP
);
```

好处：

```text
1. 快速画收益曲线
2. 快速回看某天为什么选这些股票
3. 不用反复重算历史结果
4. 方便对比不同策略表现
5. 方便后期做策略淘汰和优化
```

---

## 18. 推送模块

### 18.1 推送渠道

MVP 阶段只使用：

```text
飞书机器人
```

暂不做：

```text
企业微信机器人
Telegram Bot
邮件
网页通知
APP 通知
```

### 18.2 推送频率

建议 MVP 先做每日 1 次收盘推送。

```text
15:30 ~ 18:00 收盘后推送日报
```

后续可扩展为：

```text
09:00 盘前计划
12:00 午间监控
15:30 收盘复盘
实时重大风险提醒
```

### 18.3 飞书日报内容

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

### 18.4 推送示例

```text
【量化系统收盘日报】

日期：2026-xx-xx
市场状态：震荡
原因：上涨家数略多于下跌家数，但成交额未明显放大，热点轮动较快。

今日评级：
S 级：3 只
A 级：12 只
B 级：35 只

Top 5：
1. xxxxxx，总分 88，趋势强，资金放大，资讯正面
2. xxxxxx，总分 84，低位放量，突破 MA20
3. xxxxxx，总分 82，业绩增长，资金流入

题材拥挤度：
- xxx 概念：高拥挤，S 降 A，不追高
- xxx 概念：中拥挤，降低仓位

虚拟账户：
策略账户收益：+1.2%
基准账户收益：+0.4%
超额收益：+0.8%
最大回撤：-3.5%

今日动作：
- 新增虚拟买入：2 只
- 清仓：1 只
- 降级观察：3 只

风险提醒：
市场仍处震荡，不建议扩大仓位。
```

---

## 19. 技术架构

### 19.1 MVP 技术栈

```text
Python
FastAPI，可选
PostgreSQL 或 SQLite
APScheduler / Celery
AkShare / Tushare
LLM API
飞书机器人 Webhook
Markdown / CSV 报告
```

### 19.2 MVP 项目结构

```text
quant-system/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── scheduler.py
│   ├── data_collectors/
│   │   ├── quote_collector.py
│   │   ├── news_collector.py
│   │   └── fundamental_collector.py
│   ├── factors/
│   │   ├── trend_factor.py
│   │   ├── money_factor.py
│   │   ├── fundamental_factor.py
│   │   ├── news_factor.py
│   │   ├── risk_factor.py
│   │   ├── market_state_factor.py
│   │   └── crowding_factor.py
│   ├── strategies/
│   │   ├── trend_strategy.py
│   │   ├── breakout_strategy.py
│   │   ├── value_growth_strategy.py
│   │   └── risk_filter_strategy.py
│   ├── scoring/
│   │   └── score_engine.py
│   ├── paper_trading/
│   │   ├── virtual_account.py
│   │   └── benchmark_account.py
│   ├── snapshot/
│   │   └── strategy_snapshot.py
│   ├── notification/
│   │   └── feishu_push_service.py
│   └── reports/
│       └── daily_report.py
├── docs/
│   └── quant_mvp_plan.md
├── reports/
│   ├── daily_md/
│   └── csv/
└── README.md
```

---

## 20. MVP 开发阶段规划

### Phase 0：项目骨架，1 周

目标：搭好基础框架。

```text
- 明确股票市场范围
- 确定数据源
- 建数据库表
- 搭定时任务
- 拉取 A 股基础数据
- 拉取日 K 数据
- 生成第一份本地 Markdown 日报
```

交付物：

```text
能每天自动更新股票基础数据和行情数据。
```

### Phase 1：因子评分，2 周

目标：让系统能每日选股和评级。

```text
- 实现趋势因子
- 实现资金因子
- 实现基础财务因子
- 实现风险因子
- 实现综合评分
- 实现 S/A/B/C/D/R 评级
- 输出每日 Top 50 股票
```

交付物：

```text
每天收盘后生成：
- Top 50 股票
- S 级股票
- A 级股票
- 风险剔除股票
```

### Phase 2：市场状态 + 拥挤度，1 ~ 2 周

目标：避免在市场风险较高时盲目选股。

```text
- 实现市场状态判断
- 实现市场状态对仓位的约束
- 实现题材拥挤度轻量判断
- 实现拥挤度对评级的调整
```

交付物：

```text
系统能判断：
- 今天是进攻、震荡还是防守
- 哪些题材过热
- 是否应该降低仓位或停止开仓
```

### Phase 3：资讯抓取 + LLM 结构化，2 周

目标：让系统知道“为什么涨”，但不让 LLM 直接决定买卖。

```text
- 抓公告
- 抓新闻
- 识别股票代码
- LLM 提取事件类型
- LLM 提取关键词
- LLM 输出置信度
- 规则引擎计算资讯分
- 写入 news_events
```

交付物：

```text
每只股票都有资讯摘要、事件类型、置信度和资讯分。
```

### Phase 4：虚拟跑盘 + 基准对比，2 周

目标：验证策略是否真的有效。

```text
- 建策略虚拟账户
- 建基准虚拟账户
- 实现虚拟买入
- 实现虚拟卖出
- 计算收益率
- 计算超额收益
- 计算最大回撤
- 计算胜率
- 计算盈亏比
```

交付物：

```text
系统每天能回答：
- 策略赚没赚钱？
- 是否跑赢基准？
- 是否跑赢无脑追涨？
- 回撤是否可接受？
```

### Phase 5：strategy_daily_snapshot + 飞书推送，1 周

目标：让系统每天自动复盘并推送。

```text
- 写入 strategy_daily_snapshot
- 生成 Markdown 日报
- 生成 CSV 数据
- 接入飞书机器人
- 每日收盘后自动推送
```

交付物：

```text
每天飞书收到完整收盘日报。
```

---

## 21. MVP 最小闭环

每日收盘后：

```text
1. 更新行情数据
2. 更新财务数据
3. 抓取公告和资讯
4. LLM 提取事件信息
5. 规则引擎计算资讯分
6. 计算市场状态
7. 计算题材拥挤度
8. 计算个股多因子评分
9. 生成 S/A/B/C/D/R 评级
10. 策略虚拟账户调仓
11. 基准账户同步更新
12. 计算超额收益、最大回撤、胜率
13. 写入 strategy_daily_snapshot
14. 生成 Markdown / CSV 报告
15. 飞书机器人推送日报
```

第二天：

```text
1. 观察评分变化
2. 记录虚拟买卖结果
3. 复盘策略是否有效
4. 观察是否跑赢基准
5. 调整因子权重或策略规则
```

---

## 22. 后期迭代路线

### V1.1：策略回测

```text
- 支持单策略回测
- 支持多策略对比
- 支持手续费和滑点
- 支持调仓周期
- 支持收益曲线
- 支持最大回撤
- 支持夏普比率
```

### V1.2：板块强度系统

```text
- 行业涨幅排名
- 概念涨幅排名
- 板块成交额排名
- 板块资金流入排名
- 板块内龙头识别
- 主线持续性判断
```

### V1.3：策略优化

```text
- 参数自动寻优
- 不同市场环境下策略切换
- 趋势市用趋势策略
- 震荡市用低吸策略
- 弱市降低仓位
- 策略表现差则自动降权
```

### V1.4：AI 研究员模块

AI 研究员只负责解释和总结，不直接给买卖指令。

输入：

```text
股票代码
最近走势
财务数据
新闻公告
所属板块
评分变化
市场状态
题材拥挤度
```

输出：

```text
一句话结论
上涨逻辑
风险点
是否值得观察
适合短线还是中线
置信度
```

### V1.5：轻量 Web Dashboard，可选

只有当飞书机器人和本地报告已经满足不了使用时，再考虑加 Web 页面。

```text
- 首页 Dashboard
- 选股列表
- 股票详情
- 虚拟账户收益曲线
- 策略表现对比
- 资讯中心
```

### V2.0：半自动交易

```text
- 接入券商接口
- 只生成交易建议
- 人工确认下单
- 自动记录真实交易
- 对比真实交易和虚拟交易
```

### V3.0：自动交易，谨慎

只有满足以下条件才考虑：

```text
- 虚拟跑盘至少 3 ~ 6 个月
- 多种市场环境下表现稳定
- 策略长期跑赢基准
- 最大回撤可接受
- 实盘小资金测试通过
- 有完整风控
- 有异常熔断
```

---

## 23. 最终 MVP 版本定义

最终 MVP 不做复杂平台，而是做一个：

> **Python 定时任务 + 数据库 + 多因子评分 + LLM 资讯结构化 + 市场状态控制 + 拥挤度判断 + 虚拟跑盘 + 基准对比 + 飞书日报推送**

核心能力：

```text
1. 自动发现机会
2. 自动评分评级
3. 自动判断市场环境
4. 自动识别过热题材
5. 自动验证策略有效性
6. 自动记录每日策略快照
7. 自动推送复盘日报
```

一句话总结：

> 这是一个以“策略有效性验证”为核心的 A 股量化选股 MVP，而不是一个简单的股票推荐工具。
