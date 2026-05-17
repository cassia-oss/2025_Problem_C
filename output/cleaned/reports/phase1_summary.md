# Phase 1 Summary — Data Preprocessing Checkpoint

> **日期**：2026-05-10
> **对应**：PIPELINE.md Section 1 + Section 6 (After Phase 1 checklist)

---

## 1. 完成步骤

| Step | 脚本 | 输入 | 输出 | 状态 |
|---|---|---|---|---|
| 1.5 | NOC 统一表 | 全部 4 个数据集 | `noc_mapping_v2.csv` | ✅ |
| 1.1 | 运动员数据清洗 | `summerOly_athletes.csv` | `athletes_clean.csv` | ✅ |
| 1.2 | 奖牌数据构建 | `athletes_clean.csv` + `noc_mapping_v2.csv` | `medal_counts_clean.csv` | ✅ |
| 1.3 | 项目数据清洗 | `summerOly_programs.csv` | `programs_clean.csv` | ✅ |
| 1.4 | 主办国数据清洗 | `summerOly_hosts.csv` | `hosts_clean.csv` | ✅ |

副产物：
- `medal_counts_compare.csv` — athletes-derived vs IOC 官方对比
- `dup_medal_conflict.csv` — Type B-P2 原始冲突组（21 组）
- `bp2_audit.csv` — B-P2 每行删除原因审计（41 行）

---

## 2. NOC 统一表 (`noc_mapping_v2.csv`)

| 指标 | 值 |
|---|---|
| 总行数 | 4,564 |
| 唯一 athlete_NOC | 234 |
| 唯一 canonical_name | 231 |
| Year 范围 | 1896–2024 |

- `canonical_name` 是项目统一标识符，所有下游 join 均使用 NOC → canonical_name 桥接
- Team 列不做标准化替换——NOC（3 字母 IOC 代码）是唯一 join key（决策 D09）
- `NOC_in_medal_counts` 列仅在对比官方表时使用

---

## 3. 运动员数据 (`athletes_clean.csv`)

```
252,565 行 (原始)
  → 251,009 行 (清洗后)
  → -1,556 行 (去重)
```

| 去重类型 | 组数 | 处理 |
|---|---|---|
| Type A (完全重复) | 676 | drop_duplicates() |
| Type B-P1 (奖牌 vs 无奖牌) | 67 | 保留奖牌行 |
| Type B-P2 (奖牌冲突) | 21 | 约束裁决：以官方总数为约束，优先删超额的奖牌类型（详见 bp2_audit.csv），无 fallback |
| Type C (多船参赛 1900) | 9 | 全部保留 |

- `is_multi_team`: 2,713 行标记（350 个独特 Team 名含 -1/-2 后缀）
- 乱码检查：0 个问题（3 个合法非 ASCII 名：Côte d'Ivoire, São Tomé and Príncipe, Türkiye）

---

## 4. 奖牌数据 (`medal_counts_clean.csv`)

### 方法论

从 athletes 衍生，非 IOC 官方表。理由（D01）：兴奋剂追溯取消和政治性奖牌重分配不代表赛场竞争趋势，模型应学习"赛场实际表现"。

### 结构

- **3,222 行** — 完整 (NOC, Year) 面板，含零奖牌参赛国
- 231 个 canonical_name
- 31 个 Olympiad（含 1906）
- 18,121 枚奖牌总计

### 与 IOC 官方对比

| 状态 | 行数 | 占比 |
|---|---|---|
| MATCH | 1,251 | 87.5%（占可比行） |
| DIFFER | 179 | 12.5% |
| ONLY_IN_ATHLETES | 1,792 | 零奖牌 + 1906 等 |
| ONLY_IN_OFFICIAL | 4 | 官方独有 |

差异集中在 2008/2012/2024（差异 >1 枚的情况主要在近几届），原因：兴奋剂 DQ、双铜牌、2020/2024 数据不完整。详见 `medal_counts_compare.csv`。

### 校验

- (NOC, Year) 唯一性：0 重复
- NOC 为空：0 行
- Gold + Silver + Bronze == Total：0 违规

---

## 5. 项目数据 (`programs_clean.csv`)

| 指标 | 值 |
|---|---|
| 行数 | 2,201 |
| Sport | 48 |
| Discipline | 68 |
| Year 范围 | 1896–2024 |

### 特殊值处理（D08）

| 原始值 | 含义 | EventCount | is_demo | status_code |
|--------|------|------------|---------|-------------|
| `?0`, `??0` | 演示项目，0 事件 | 0 | 1 | demo |
| `?4`, `??1` | 演示项目，N 事件 | N | 1 | demo |
| `0[s3]` | 天气取消 | 0 | 0 | cancelled_weather |
| `Included in winter games...[s5]` | 转冬奥 | 0 | 0 | winter_transfer |

- is_demo=1: 23 行
- status_code 分布：official (2,174) / demo (23) / cancelled_weather (2) / winter_transfer (2)

---

## 6. 主办国数据 (`hosts_clean.csv`)

- 35 行（30 已举办 + 2 未来 + 3 取消）
- 取消年份 (1916/1940/1944)：NOC='CANCELLED', canonical_name='CANCELLED'
- 未来年份 (2028/2032)：已分配 NOC 和 canonical_name
- `is_cancelled` 和 `is_future` 布尔标记

---

## 7. 全局口径决策

| ID | 决策 |
|----|------|
| D01 | Medal counts 以 athletes 为准（非 IOC 官方） |
| D07 | 1906 Intercalated Games 纳入全部数据集和 OLYMPIC_YEARS |
| D08 | Programs 增加 status_code 列，修复 demo 检测 |
| D09 | Team 名不做标准化——下游必须用 NOC join，通过 mapping 桥接到 canonical_name |
| D10 | hosts 取消年份使用 'CANCELLED' 哨兵值填充 NOC/canonical_name |

---

## 8. Verification Checklist (PIPELINE Section 6)

- [x] `athletes_clean.csv` row count ≈ 251,009
- [x] All NOC values in athletes match `noc_mapping_v2.csv`
- [x] No garbled Team names remain
- [x] `medal_counts_clean.csv`: (NOC, Year) unique, NOC not null, Gold+Silver+Bronze==Total
- [x] `medal_counts_clean.csv`: includes zero-medal participation rows (complete panel)

---

## 9. 已知风险 & 待处理

| # | 问题 | 优先级 | 状态 |
|---|------|--------|------|
| 11 | NOC mapping 中 NOC_in_medal_counts 覆盖不足（仅影响对比表 1 行） | 低 | 待修 |
| 14 | tests/ 目录为空，无自动化回归保护 | 高 | 待补 |
| — | 2020/2024 运动员数据可能不完整 | 低 | 持续关注 |
