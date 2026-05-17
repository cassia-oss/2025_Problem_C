# Olympic NOC Historical Changes Reference

> 用途：解释 medal_counts 和 athletes 中出现的所有历史国家名称及其演变关系。
> 配套文件：`noc_mapping_v2.csv`（年份感知的完整 NOC 映射表）。
> 用于 NOC 映射表人工复核、论文"数据假设"部分撰写。

---

## 0. noc_mapping_v2.csv — 列定义

文件位置：`output/cleaned/noc_mapping_v2.csv`
行数：4,564 行
编码：UTF-8

| 列名 | 数据类型 | 说明 |
|---|---|---|
| `athlete_NOC` | string(3) | athletes 表中的 3 位 NOC 代码（如 AFG, USA, TUR） |
| `athlete_Team` | string | athletes 表中该 NOC 在某年使用的 Team 名称（如 "Afghanistan", "United States-1", "Gitana-2"） |
| `Year` | int | 夏季奥运会年份（1896–2024，含 1906 届间运动会） |
| `NOC_in_medal_counts` | string | 该 (athlete_NOC, Year) 在 medal_counts 中对应的名称。**用此列 + Year 去 medal_counts 查询奖牌数。** |
| `match_in_medal` | enum | 匹配状态（见下方详细说明） |
| `canonical_name` | string | 统一标准名。`historical_same` 类型映射到现代名称；`historical_different` 保留历史名称 |
| `entity_type` | enum | 实体分类：`country`, `historical_same`, `historical_different`, `special` |

### match_in_medal 各值含义

| 值 | 数量 | 含义 | NOC_in_medal_counts 是否有值 | 示例 |
|---|---|---|---|---|
| `YES` | 2,660 | athlete_Team 同年出现在 medal_counts 中，或通过历史名映射成功 | ✅ 有值 | AFG 2008 Team="Afghanistan" → NOC_in_medal="Afghanistan" |
| `NO_DIFF_YEAR` | 1,137 | 该 canonical_name 在 medal_counts 中存在，但当年未获奖牌（或 Team 名不匹配） | ❌ 空 | AFG 1936 Team="Afghanistan" — 参赛但 1936 年未获奖 |
| `NO` | 762 | 该 NOC 从未在 medal_counts 中出现（无奖牌国家、俱乐部名、船名） | ❌ 空 | AND (安道尔) 任何年份、FRA 的 "Gitana-2"（帆船名） |
| `HISTORICAL` | 5 | 已标注历史名称，但 medal_counts 中该年无对应条目（该国那届未获奖） | ✅ 有值 | RUS 1900 Team="Russia" → NOC_in_medal="Russian Empire"（但 1900 沙俄未获奖牌） |

### 使用方式（Python 代码示例）

```python
import pandas as pd
from pathlib import Path

# 载入映射表
mapping = pd.read_csv('output/cleaned/noc_mapping_v2.csv')

# 用法 1：查询某国某年在 medal_counts 中叫什么名字
row = mapping[(mapping['athlete_NOC'] == 'RUS') & (mapping['Year'] == 1908)]
print(row['NOC_in_medal_counts'].values[0])  # → "Russian Empire"

# 用法 2：获取所有可以用 match_in_medal='YES' 查询 medal_counts 的行
valid = mapping[mapping['match_in_medal'] == 'YES']

# 用法 3：用 canonical_name 统一所有历史名称
fra_teams = mapping[mapping['canonical_name'] == 'France']['athlete_Team'].unique()
# → array(['Alcyon-6', 'Alcyon-7', ..., 'France', 'France-1', ...])

# 用法 4：区分 historical_same（合并）和 historical_different（不合并）
same  = mapping[mapping['entity_type'] == 'historical_same']
diff  = mapping[mapping['entity_type'] == 'historical_different']
# same 的 canonical_name 统一到现代名；diff 保留各自历史名
```

---

## 分类标准

| entity_type | 含义 | 处理方式 | 数量 |
|---|---|---|---|
| `country` | 从首次参加至今连续存在的国家实体 | 直接使用 | 4,359 |
| `historical_same` | 同一领土实体，仅名称改变 | canonical_name 为最新名称 | 45 |
| `historical_different` | 已消亡的政治实体，领土不等于任何单一现代国家 | canonical_name 保留历史名称，不合并 | 147 |
| `special` | 非国家实体（难民队、独立运动员、混合队、中立运动员） | 保留原始标记 | 13 |

### special 实体完整列表

| athlete_NOC | canonical_name | 出现年份 | NOC_in_medal_counts | 说明 |
|---|---|---|---|---|
| AIN | Individual Neutral Athletes | 2024 | — | 俄罗斯/白俄罗斯中立运动员（2024巴黎） |
| EOR | Refugee Olympic Team | 2016, 2020, 2024 | Refugee Olympic Team | 难民奥运代表队 |
| IOA | Individual Olympic Athletes | 1992, 2000, 2012, 2016 | Independent Olympic Athletes | 无NOC代表的独立运动员（注意：medal_counts 用 "Independent" 而非 "Individual"） |
| IOP | Independent Olympic Participants | 1992 | Independent Olympic Participants | ⚠️ 仅存在于 medal_counts，athletes 中无记录。1992巴塞罗那，南斯拉夫制裁期间独立参赛者 |
| ROC | Russia | 2020 | ROC | 俄罗斯奥林匹克委员会（2020东京，因禁赛以中立身份参赛） |
| UNK | Unknown | 1900 | — | 运动员国籍未知 |
| ZZX | Mixed team | 1896, 1900, 1904 | Mixed team | ⚠️ 仅存在于 medal_counts，athletes 中无记录。早期奥运会跨国混合队 |

> ⚠️ **IOP 和 ZZX 是 medal_counts-only 实体**：它们在 athletes 数据中没有对应行。
> 其 `athlete_Team` 列为空字符串，仅用于 medal_counts 查询。若未来从外部数据源获取这些运动员记录，可按 `athlete_NOC` 回填。

---

## I. historical_same — 同一实体，名称变更

### Formosa → Taiwan → Chinese Taipei (台湾/中华台北)

| 年份 | 使用的名称 | 原因 |
|------|-----------|------|
| 1956-1960 | **Formosa** | IOC 强加的折中名称，台湾方面抗议 |
| 1964-1968 | **Taiwan** | 与 "Republic of China" 并列使用 |
| 1972 | Republic of China | 最后一次使用 "China" |
| 1976 | 抵制/退出 | 加拿大拒绝 "Republic of China" 名称 |
| 1981 | **洛桑协议** | 确定使用 **Chinese Taipei**、新旗、新歌 |
| 1984-至今 | **Chinese Taipei** (TPE) | 现行名称 |

→ **映射表中所有 Formosa / Taiwan / Chinese Taipei 统一为 `Chinese Taipei` (canonical_name)**
→ NOC_in_medal_counts 保留各年份实际名称：1956-1964→"Formosa", 1968→"Taiwan", 1984+→"Chinese Taipei"

### Ceylon → Sri Lanka (斯里兰卡)

| 年份 | 名称 | 原因 |
|------|------|------|
| 1948-1972 | **Ceylon** | 英国殖民地时期名称 |
| 1972-至今 | **Sri Lanka** (SRI) | 1972年改国名 |

→ **统一为 `Sri Lanka`**。1948 年 NOC_in_medal_counts="Ceylon"

### Macedonia → North Macedonia (北马其顿)

| 年份 | 名称 | 原因 |
|------|------|------|
| 1996-2016 | **Macedonia** | 与希腊存在名称争议 |
| 2019 | **普雷斯帕协议** | 正式更名为 North Macedonia |
| 2020-至今 | **North Macedonia** (MKD) | 现行名称 |

→ **统一为 `North Macedonia`**

### Ivory Coast / Côte d'Ivoire

| 年份 | 名称 | 原因 |
|------|------|------|
| 1964-至今 | **Ivory Coast** (CIV) | IOC 使用英文名，未随国名法语化变更 |

→ **保留 IOC 使用的 `Ivory Coast`**

### Russian Empire → Russia (沙俄 → 俄罗斯联邦)

| 年份 | medal_counts 名称 | 说明 |
|------|------------------|------|
| 1900, 1908, 1912 | **Russian Empire** | 沙俄时期。athletes 中 NOC=RUS, Team="Russia" |
| 1996-至今 | **Russia** | 俄罗斯联邦 |

→ **统一为 `Russia` (canonical_name)**。NOC_in_medal_counts 保留 "Russian Empire" 用于 1900-1912 查询

---

## II. historical_different — 已消亡的政治实体

### 苏联及其相关实体

| 实体 | 年份范围 | 说明 | 继承关系 |
|------|---------|------|---------|
| Russian Empire | 1900-1912 | 沙俄 | → Soviet Union |
| Soviet Union (URS) | 1952-1988 | 苏联，15个加盟共和国 | → 1991年解体为15国 |
| Unified Team (EUN) | 1992 | 独联体联队（除波罗的海三国外的12个前苏联共和国） | → 各国独立参赛 |
| ROC | 2020 | 俄罗斯奥林匹克委员会（禁赛期间的中立身份） | → 2024年以 AIN 身份 |
| Russia (RUS) | 1996-2016 | 俄罗斯联邦 | 苏联的继承国之一 |

**关键原则：URS / EUN / RUS / ROC 是四个不同的政治实体，除 Russian Empire→Russia (historical_same) 外，不合并。**

```python
# 查询苏联历年奖牌
sov = mapping[(mapping['athlete_NOC'] == 'URS') & (mapping['match_in_medal'] == 'YES')]
# sov['NOC_in_medal_counts'] 均为 "Soviet Union"
# sov['Year'] 范围: 1952, 1956, 1960, 1964, 1968, 1972, 1976, 1980, 1988
```

苏联解体产生的15个国家：Russia, Ukraine, Belarus, Kazakhstan, Kyrgyzstan, Uzbekistan, Turkmenistan, Tajikistan, Azerbaijan, Armenia, Georgia, Moldova, Lithuania, Latvia, Estonia

### 德国相关实体

| 实体 | 年份范围 | 说明 |
|------|---------|------|
| Germany (GER) | 1896-1936, 1992-至今 | 统一德国 |
| United Team of Germany (EUA) | 1956-1964 | 东西德联合组队。medal_counts 写 "United Team of Germany"，athletes 写 GER/Team="Germany" |
| East Germany (GDR) | 1968-1988 | 东德，1990年并入联邦德国 |
| West Germany (FRG) | 1968-1988 | 西德，1990年统一 |

**关键原则：1990年前的 GDR/FRG 独立存在。1990年后统一为 Germany。EUA (1956-1964) 是 transitional 实体。**

```python
# GER 在 1956/1960/1964 的特殊处理
ger_1956 = mapping[(mapping['athlete_NOC'] == 'GER') & (mapping['Year'] == 1956)]
# NOC_in_medal_counts = "United Team of Germany"
# → 用此名去 medal_counts 查询奖牌
```

### 南斯拉夫相关实体

| 实体 | 年份范围 | 说明 |
|------|---------|------|
| Yugoslavia (YUG) | 1920-1988 | 南斯拉夫社会主义联邦共和国 |
| FR Yugoslavia | 1996-2000 | 仅剩塞尔维亚+黑山。medal_counts 写 "FR Yugoslavia"，athletes 使用 SCG/Team="Serbia and Montenegro" |
| Serbia and Montenegro (SCG) | 2004-2006 | 塞尔维亚和黑山国家联盟 |
| Serbia (SRB) | 2008-至今 | 塞尔维亚 |
| Montenegro (MNE) | 2008-至今 | 黑山 |

```python
# SCG 的 medal_counts 名称随时间变化
scg_1996 = mapping[(mapping['athlete_NOC'] == 'SCG') & (mapping['Year'] == 1996)]
# NOC_in_medal_counts = "FR Yugoslavia"
scg_2004 = mapping[(mapping['athlete_NOC'] == 'SCG') & (mapping['Year'] == 2004)]
# NOC_in_medal_counts = "Serbia and Montenegro"
```

其他从南斯拉夫独立的国家：Croatia (CRO), Slovenia (SLO), Bosnia and Herzegovina (BIH), North Macedonia (MKD), Kosovo (KOS)

### 捷克斯洛伐克

| 实体 | 年份范围 | 说明 |
|------|---------|------|
| Bohemia (BOH) | 1900-1912 | 奥匈帝国内的波西米亚地区 |
| Czechoslovakia (TCH) | 1920-1992 | 捷克斯洛伐克 |
| Czech Republic (CZE) | 1996-至今 | 捷克共和国（1993年分裂） |
| Slovakia (SVK) | 1996-至今 | 斯洛伐克（1993年分裂） |

**关键原则：Bohemia → Czechoslovakia → Czech Republic 是不同实体，不合并。**

### 其他已消亡实体

| 实体 | 年份范围 | 说明 |
|------|---------|------|
| Australasia (ANZ) | 1908-1912 | 澳大利亚+新西兰联队，之后分开参赛 |
| British West Indies (BWI) | 1960 | 西印度群岛联邦（1958-1962）。medal_counts 写 "British West Indies"，athletes 使用 WIF NOC |
| Netherlands Antilles (AHO) | 1952-2008 | 荷属安的列斯，2010年解散 |
| United Arab Republic (UAR) | 1960-1968 | 埃及+叙利亚短暂联盟，之后仅埃及沿用 |
| North Borneo (NBO) | 1956 | 英属北婆罗洲，1963年并入马来西亚 |
| North Yemen (YAR) | 1984-1988 | 北也门，1990年与南也门统一为也门 |
| South Yemen (YMD) | 1988 | 南也门，1990年与北也门统一为也门 |
| South Vietnam (VNM) | 1952-1972 | 南越，1976年与北越统一 |
| Saar (SAA) | 1952 | 萨尔保护领，1957年并入西德 |
| Rhodesia (RHO) | 1960-1964 | 罗德西亚，现津巴布韦 |
| Malaya (MAL) | 1956-1960 | 马来亚联合邦，1963年改组为马来西亚 |
| Newfoundland (NFL) | 1904 | 纽芬兰，1949年并入加拿大 |
| Crete (CRT) | 1906 | 克里特岛，1913年并入希腊 |

---

## III. special — 非国家实体（完整列表）

| athlete_NOC | canonical_name | 出现年份 | NOC_in_medal_counts | 说明 |
|---|---|---|---|---|
| AIN | Individual Neutral Athletes | 2024 | — | 俄罗斯/白俄罗斯中立运动员（2024巴黎）。athletes 中 Team 名即为 "AIN" |
| EOR | Refugee Olympic Team | 2016, 2020, 2024 | Refugee Olympic Team | 难民奥运代表队。medal_counts 中写 "Refugee Olympic Team" |
| IOA | Individual Olympic Athletes | 1992, 2000, 2012, 2016 | Independent Olympic Athletes | ⚠️ medal_counts 用 "Independent"，athletes 用 "Individual"——两者指同一实体 |
| IOP | Independent Olympic Participants | 1992 | Independent Olympic Participants | ⚠️ **medal_counts-only 实体**。仅 1992 巴塞罗那。58 名运动员（52 南斯拉夫 + 6 马其顿），athletes 中无 IOP NOC |
| ROC | Russia | 2020 | ROC | 俄罗斯奥林匹克委员会。athletes 中 NOC=ROC, Team="Russia"，canonical_name="Russia" |
| UNK | Unknown | 1900 | — | 国籍未知的运动员（仅 1900 年早期记录） |
| ZZX | Mixed team | 1896, 1900, 1904 | Mixed team | ⚠️ **medal_counts-only 实体**。早期奥运会不同国籍运动员混合组队。共获 25 枚奖牌 |

### IOP 和 ZZX 的特殊处理

```python
# 这两个实体在 mapping 中只有 4 行（athlete_Team 为空）
import pandas as pd
mapping = pd.read_csv('output/cleaned/noc_mapping_v2.csv')
medal_only = mapping[mapping['athlete_Team'] == '']
print(medal_only[['athlete_NOC', 'Year', 'NOC_in_medal_counts', 'entity_type']])

# 输出：
#   athlete_NOC  Year  NOC_in_medal_counts                  entity_type
# 0 IOP          1992  Independent Olympic Participants     special
# 1 ZZX          1896  Mixed team                           special
# 2 ZZX          1900  Mixed team                           special
# 3 ZZX          1904  Mixed team                           special

# 查询 IOP 1992 年奖牌
iop_medals = pd.read_csv('data/summerOly_medal_counts.csv')
iop_medals['NOC_clean'] = iop_medals['NOC'].str.replace('\xa0', '').str.strip()
iop_1992 = iop_medals[(iop_medals['NOC_clean'] == 'Independent Olympic Participants') & 
                       (iop_medals['Year'] == 1992)]
# → 1 银 2 铜（Jasna Šekarić 等射击运动员）
```

---

## IV. 其他值得注意的命名差异

这些是 athletes 中 Team 名称与 medal_counts 中 IOC 官方名称不一致的情况：

| athletes Team 示例 | medal_counts NOC | 原因 |
|-------------------|-----------------|------|
| United States-1, United States-2 | United States | 沙滩排球、赛艇等多队参赛项目 |
| Great Britain | Great Britain | 一致（非 United Kingdom） |
| China | China | 一致（非 People's Republic of China） |
| Congo (Brazzaville) | Congo (Brazzaville) | IOC 区分两个刚果的方式 |
| Congo (Kinshasa) | DR Congo | 刚果民主共和国 |
| Hong Kong | Hong Kong | IOC 中港澳台均单独参赛 |
| Puerto Rico | Puerto Rico | 美国海外领土，IOC 中独立参赛 |
| Virgin Islands | Virgin Islands | 美属维尔京群岛，IOC 中独立参赛 |
| Individual Olympic Athletes | Independent Olympic Athletes | ⚠️ IOC 用词不一致（athletes 用 "Individual"，medal_counts 用 "Independent"） |
| Germany (GER, 1956-1964) | United Team of Germany | EUA 时期，athletes 仍写 "Germany" 为 Team 名 |
| Russia (ROC, 2020) | ROC | 2020 禁赛期间，athletes NOC=ROC 但 Team="Russia" |

---

## V. medal_counts \xa0 污染问题

medal_counts 的 NOC 列中有 49 个值带有尾部 `\xa0`（不间断空格），导致视觉上相同的名称被计算机视为不同值。

```python
# 清洗方法
medals_df['NOC_clean'] = medals_df['NOC'].astype(str).str.replace('\xa0', '', regex=False).str.strip()
# 清洗后：210 个唯一值 → 164 个唯一值（去除了 46 个假重复）
```

受影响的国家示例（清洗前后对比）：

```
repr('Argentina\xa0')  → 清洗为 'Argentina'
repr('France\xa0')     → 清洗为 'France'
repr('Turkey\xa0')     → 清洗为 'Turkey'
... 共 49 个
```

此问题已在 `noc_mapping_v2.csv` 生成前处理完毕。所有 `NOC_in_medal_counts` 值均为清洗后的名称。

---

## 附录：mapping 表统计摘要

| 指标 | 值 |
|---|---|
| 总行数 | 4,564 |
| 唯一 athlete_NOC | 234 |
| 唯一 athlete_Team | 1,193 |
| 唯一 canonical_name | 233 |
| 唯一 NOC_in_medal_counts（非空） | 164 |
| 年份范围 | 1896–2024 |
| medal_counts-only 实体 | IOP, ZZX（2 个实体，4 行） |
