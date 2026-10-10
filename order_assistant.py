#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话点餐助手 · 最小可运行演示（order_assistant.py）

基于麦当劳 MCP（https://mcp.mcd.cn）的对话式点餐闭环演示脚本。
对应 SKILL.md 的 S1(定位)→S2(读菜单)→S3(选品)→S4(算价) 状态机，
到 S5(下单) 前停止，不产生真实订单。

运行方式：
    set MCD_MCP_TOKEN=<你的Token>          # Windows
    python order_assistant.py 北京 王府井   # 城市 + 商圈/地标关键词

安全说明：Token 仅从环境变量读取，本文件不含任何凭证。
"""

import json
import os
import sys
import urllib.request

URL = "https://mcp.mcd.cn"


class MCDClient:
    """麦当劳 MCP 客户端（Streamable HTTP + JSON-RPC，UTF-8 中文编码）。"""

    def __init__(self, token: str):
        self.token = token
        self._id = 0

    def rpc(self, method: str, params=None):
        self._id += 1
        payload = {"jsonrpc": "2.0", "id": self._id, "method": method,
                   "params": params or {}}
        headers = {
            "Content-Type": "application/json; charset=utf-8",  # 中文参数必需
            "Accept": "application/json, text/event-stream",
            "Authorization": "Bearer " + self.token,
        }
        req = urllib.request.Request(
            URL, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers, method="POST")
        resp = urllib.request.urlopen(req, timeout=40)
        body = resp.read().decode("utf-8", errors="replace").strip()
        if body.startswith("event:") or "\ndata:" in body or body.startswith("data:"):
            for line in body.splitlines():
                if line.startswith("data:"):
                    body = line[5:].strip()
                    break
        return json.loads(body)

    def call(self, name: str, arguments: dict):
        r = self.rpc("tools/call", {"name": name, "arguments": arguments})
        return r.get("result", {}).get("structuredContent")


def search_drive_thru(c: MCDClient, city: str, keyword: str):
    """S1 定位：查得来速（beType=5）门店，返回最近的 storeCode/beCode。"""
    sc = c.call("query-nearby-stores",
                {"beType": 5, "searchType": 2, "city": city, "keyword": keyword})
    data = (sc or {}).get("data") or []
    if not data:
        raise SystemExit(f"未找到得来速门店：{sc and sc.get('message')}")
    first = data[0]
    print(f"[S1] 最近门店：{first.get('storeName')}（距离 {first.get('distance')} 米）")
    return first["storeCode"], first["beCode"]


def list_menu(c: MCDClient, store_code: str, be_code: str):
    """S2 读菜单：返回 categories（每类含 meals[].code）。"""
    m = c.call("query-meals", {"storeCode": store_code, "orderType": 1,
                               "beType": 5, "beCode": be_code})
    cats = (m or {}).get("data", {}).get("categories", [])
    print(f"[S2] 菜单共 {len(cats)} 类：")
    for cat in cats:
        codes = [meal["code"] for meal in cat.get("meals", [])]
        print(f"    - {cat['name']}（{len(codes)} 项）")
    return cats


def meal_detail(c: MCDClient, store_code: str, be_code: str, code: str):
    """S3 选品：查套餐组成（名称 + rounds 子项）。"""
    d = c.call("query-meal-detail", {"storeCode": store_code, "orderType": 1,
                                     "beType": 5, "beCode": be_code, "code": code})
    return (d or {}).get("data")


def calc_price(c: MCDClient, store_code: str, be_code: str, code: str):
    """S4 算价：返回总价与 takeWayCode（下单必传）。"""
    p = c.call("calculate-price", {"storeCode": store_code, "orderType": 1,
                                   "beType": 5, "beCode": be_code,
                                   "items": [{"productCode": code, "quantity": 1}]})
    return (p or {}).get("data")


def main():
    if len(sys.argv) < 3:
        raise SystemExit("用法：python order_assistant.py <城市> <关键词>")
    token = os.environ.get("MCD_MCP_TOKEN", "")
    if not token:
        raise SystemExit("请先设置环境变量 MCD_MCP_TOKEN")

    city, keyword = sys.argv[1], sys.argv[2]
    c = MCDClient(token)
    c.rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                         "clientInfo": {"name": "mcd-voice-order-assistant", "version": "0.1"}})

    store_code, be_code = search_drive_thru(c, city, keyword)
    cats = list_menu(c, store_code, be_code)

    # 取第一个分类的第一个餐品做演示
    first_meal = cats[0]["meals"][0]["code"]
    detail = meal_detail(c, store_code, be_code, first_meal)
    name = (detail or {}).get("name", "未知餐品")
    print(f"[S3] 示例餐品：{name}")

    price = calc_price(c, store_code, be_code, first_meal)
    take_ways = (price or {}).get("takeWayList", [])
    print(f"[S4] 总价：¥{(price or {}).get('price', '?') / 100:.2f}"
          f"，takeWayCode：{[t['code'] for t in take_ways]}")

    print("\n[S5] 到此停止——下单（create-order）需用户显式确认，演示不产生真实订单。")


if __name__ == "__main__":
    main()
