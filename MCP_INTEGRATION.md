# MCP 集成说明

本文件说明本 Skill 实际使用的麦当劳 MCP Server、Tool、调用流程与业务价值。

## 使用的 MCP Server

- 名称：麦当劳中国 MCP（`mcd-mcp`）
- 接入地址：`https://mcp.mcd.cn`
- 传输协议：Streamable HTTP
- 鉴权：`Authorization: Bearer ${MCD_MCP_TOKEN}`
- 频控：600 次 / 分钟

## 点餐场景参数体系

麦当劳 MCP 用两个维度区分点餐场景：

| 场景 | beType | orderType | 下单关键参数 |
|---|---|---|---|
| 到店自取 | 1 | 1 | storeCode + takeWayCode |
| 得来速 | 5 | 1 | storeCode + beCode + takeWayCode |
| 麦乐送 | 2 | 2 | storeCode + beCode + addressId |
| 团餐 | 6 | 2 | gmServiceCode + addressId |

> 上表已经官方 MCP Token 实测确认（tools/list 实际 schema，2026-10-10）：`create-order` / `calculate-price` 必传 `storeCode` + `orderType` + `beType`；`beCode` 得来速 / 外送 / 团餐必传；`takeWayCode` 仅 orderType=1 必传；`query-nearby-stores` 的 beType 枚举仅 1/5，`searchType=2` 才按位置搜索。

## 实际使用的 Tool 与调用流程

| 点餐步骤 | Tool | 说明 |
|---|---|---|
| 读菜单 | `query-meals` | 查当前门店可售餐品（分类、编码、标签） |
| 套餐详情 / 替换 | `query-meal-detail` | 查套餐组成与可替换项 |
| 算价 | `calculate-price` | 按商品列表（含券）计算金额，返回 `takeWayList[].code` |
| 下单 | `create-order` | 按门店、就餐方式、商品列表下单，返回订单与支付链接 |
| 查单 / 取餐码 | `query-order` | 查订单状态与取餐信息 |
| 附近门店 | `query-nearby-stores` | 按 beType（1 到店 / 5 得来速）查附近餐厅 |
| 配送地址 | `delivery-query-addresses` / `delivery-create-address` | 麦乐送场景地址管理 |
| 可配送门店 | `delivery-query-stores` | 查收货地址附近可配送门店 |
| 优惠券 | `query-store-coupons` / `available-coupons` / `auto-bind-coupons` / `query-my-coupons` | 门店可用券 / 麦麦省领券 / 我的券 |
| 营养数据 | `list-nutrition-foods` | 餐品能量、蛋白、脂肪、碳水、钠、钙 |
| 时间 | `now-time-info` | 获取当前时间 |

### 核心调用链

**到店 / 得来速**（已实测，2026-10-10）
```
query-nearby-stores(beType=1/5, searchType=2, city+keyword 必传) → 取 storeCode/beCode
→ query-meals(storeCode, orderType=1, beType, [beCode if DT]) → 得 code+tags
→ query-meal-detail(code) → 得 name/rounds/替换项
→ calculate-price(storeCode, orderType=1, beType, [beCode if DT], items) → 得 takeWayList[].code
→ create-order(storeCode, orderType=1, beType, [beCode if DT], takeWayCode)
→ query-order(取餐码)
```

> 实测数据点（祈年大街得来速餐厅，storeCode=1950202）：`query-meals` 只返回 `code`+`tags`，名称需 `query-meal-detail`；`calculate-price` 得来速场景返回 `takeWayList = [{code:"take-dt-quick", title:"得来速", subtitle:"车道自提"}]`。

**麦乐送**
```
delivery-query-addresses / delivery-create-address → delivery-query-stores
→ query-meals → calculate-price → create-order(orderType=2) → query-order
```

## 业务价值

本 Skill 将麦当劳 MCP 的结构化点餐能力，转化为面向残障人群与驾车者的无障碍对话体验：

- **可及性**：视障 / 低视力用户无法有效使用图形界面点餐，本 Skill 用语音把菜单、价格、取餐码逐项读出，使其能独立完成一次点餐。
- **安全**：驾车者全程免手动，语音完成选餐与下单，降低驾驶分心风险。
- **效率**：行动不便者以最少对话步骤完成下单，外带 / 得来速免排队。
- **数据价值**：MCP 输出本身无视觉依赖，恰好适配无障碍场景，是「AI + MCP」在普惠方向的一次落地示范。
