# Olympic NOC Historical Changes Reference

> 用途：解释 medal_counts 和 athletes 中出现的所有历史国家名称及其演变关系。
> 用于 NOC 映射表人工复核、论文"数据假设"部分撰写。

---

## 分类标准

| entity_type | 含义 | 处理方式 |
|-------------|------|---------|
| `country` | 从首次参加至今连续存在的国家实体 | 直接使用 |
| `historical_same` | 同一领土实体，仅名称改变 | 合并为最新名称 |
| `historical_different` | 已消亡的政治实体，领土不等于任何单一现代国家 | 保留历史名称，不合并 |
| `special` | 非国家实体（难民队、独立运动员、混合队） | 保留原始标记 |

---

## I. historical_same — 同一实体，名称变更

### Formosa → Taiwan → Chinese Taipei (台湾/中华台北)

| 年份 | 使用的名称 | 原因 |
|------|-----------|------|
| 1956-1960 | **Formosa** | IOC 强加的折中名称，台湾方面抗议 |
| 1964-1968 | **Taiwan** | 与"Republic of China"并列使用 |
| 1972 | Republic of China | 最后一次使用"China" |
| 1976 | 抵制/退出 | 加拿大拒绝"Republic of China"名称 |
| 1981 | **洛桑协议** | 确定使用 **Chinese Taipei**、新旗、新歌 |
| 1984-至今 | **Chinese Taipei** (TPE) | 现行名称 |

→ **映射表中所有 Formosa / Taiwan / Chinese Taipei 统一为 `Chinese Taipei`**

### Ceylon → Sri Lanka (斯里兰卡)

| 年份 | 名称 | 原因 |
|------|------|------|
| 1948-1972 | **Ceylon** | 英国殖民地时期名称 |
| 1972-至今 | **Sri Lanka** (SRI) | 1972年改国名 |

→ **统一为 `Sri Lanka`**

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

---

## II. historical_different — 已消亡的政治实体

### 苏联及其相关实体

| 实体 | 年份范围 | 说明 | 继承关系 |
|------|---------|------|---------|
| Russian Empire | 1900-1912 | 沙俄 | → Soviet Union |
| Soviet Union (URS) | 1952-1988 | 苏联，15个加盟共和国 | → 1991年解体为15国 |
| Unified Team (EUN) | 1992 | 独联体联队（除波罗的海三国外的12个前苏联共和国） | → 各国独立参赛 |
| Russia (RUS) | 1996-至今 | 俄罗斯联邦 | 苏联的继承国之一 |

**关键原则：URS / EUN / RUS 是三个不同的政治实体，不合并。**

苏联解体产生的15个国家：Russia, Ukraine, Belarus, Kazakhstan, Kyrgyzstan, Uzbekistan, Turkmenistan, Tajikistan, Azerbaijan, Armenia, Georgia, Moldova, Lithuania, Latvia, Estonia

### 德国相关实体

| 实体 | 年份范围 | 说明 |
|------|---------|------|
| Germany (GER) | 1896-1936, 1992-至今 | 统一德国 |
| United Team of Germany (EUA) | 1956-1964 | 东西德联合组队 |
| East Germany (GDR) | 1968-1988 | 东德，1990年并入联邦德国 |
| West Germany (FRG) | 1968-1988 | 西德，1990年统一 |

**关键原则：1990年前的 GDR/FRG 独立存在。1990年后统一为 Germany。**

### 南斯拉夫相关实体

| 实体 | 年份范围 | 说明 |
|------|---------|------|
| Yugoslavia (YUG) | 1920-1988 | 南斯拉夫社会主义联邦共和国 |
| FR Yugoslavia (YUG) | 1996-2000 | 仅剩塞尔维亚+黑山，但沿用 Yugoslavia 名 |
| Serbia and Montenegro (SCG) | 2004-2006 | 塞尔维亚和黑山国家联盟 |
| Serbia (SRB) | 2008-至今 | 塞尔维亚 |
| Montenegro (MNE) | 2008-至今 | 黑山 |

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
| British West Indies (BWI) | 1960 | 西印度群岛联邦（1958-1962），解散后各国独立参赛 |
| Netherlands Antilles (AHO) | 1952-2008 | 荷属安的列斯，2010年解散 |

---

## III. special — 非国家实体

| 实体 | IOC代码 | 出现年份 | 说明 |
|------|---------|---------|------|
| Mixed team | ZZX | 1896-1904 | 早期奥运中不同国籍运动员组成的混合队 |
| Independent Olympic Athletes | IOA | 2000, 2012, 2016 | 无NOC代表的独立运动员 |
| Independent Olympic Participants | IOP | 1992 | 南斯拉夫制裁期间的独立参赛者 |
| Refugee Olympic Team | EOR | 2016-2024 | 难民奥运代表队 |

---

## IV. 其他值得注意的命名差异

这些是 athletes 中 Team 名称与 medal_counts 中 IOC 官方名称不一致的情况（非政治原因，仅命名惯例）：

| athletes Team 示例 | medal_counts NOC | 原因 |
|-------------------|-----------------|------|
| United States-1, United States-2 | United States | 沙滩排球等多队参赛项目 |
| Great Britain | Great Britain | 一致（非 United Kingdom） |
| China | China | 一致（非 People's Republic of China） |
| Congo (Brazzaville) | Congo (Brazzaville) | IOC区分两个刚果的方式 |
| Congo (Kinshasa) | DR Congo | 刚果民主共和国 |
| Hong Kong | Hong Kong | IOC 中港澳台均单独参赛 |
| Puerto Rico | Puerto Rico | 美国海外领土，IOC 中独立参赛 |
| Virgin Islands | Virgin Islands | 美属维尔京群岛，IOC 中独立参赛 |
