#!/usr/bin/env python3
"""
捡漏搜索工具 (Hidden City Search / Smart Flight Search)

功能：
- 用户搜索 A→B 单程行程
- 根据预配置的扩散城市库，搜索 A→C (在B中转一次) 的单程联程价格
- 如果 A→C 联程价格低于 A→B 直达价格，推荐捡漏方案

限制条件：
- 只支持单程，不支持往返
- 只支持一段中转的联程航班（A→B→C，恰好2个航段）

使用方法：
    python bargain_flights.py --origin "北京" --destination "上海" --dep-date "2026-04-10"
    python bargain_flights.py --origin "BJS" --destination "SHA" --dep-date "2026-04-10" --min-savings 100
"""

import argparse
import json
import subprocess
import sys
import os
import re
from datetime import datetime

# 城市三字码映射
CITY_CODE_MAP = {
    # 国内城市
    "BJS": "北京", "PEK": "北京", "PKX": "北京",
    "SHA": "上海", "PVG": "上海",
    "CAN": "广州", "SZX": "深圳", "CTU": "成都",
    "CKG": "重庆", "HGH": "杭州", "NKG": "南京",
    "WUH": "武汉", "XIY": "西安", "KMG": "昆明",
    "LJG": "丽江", "DLY": "大理", "SYX": "三亚",
    "HAK": "海口", "KWL": "桂林", "XMN": "厦门",
    "TAO": "青岛", "TSN": "天津", "CSX": "长沙",
    "CGO": "郑州", "URC": "乌鲁木齐", "LHW": "兰州",
    "INC": "银川", "HET": "呼和浩特",
    "NNG": "南宁", "KHN": "南昌", "FOC": "福州",
    "DLC": "大连", "SJW": "石家庄", "TYN": "太原",
    "YNT": "烟台", "WEH": "威海", "TNA": "济南",
    "CGQ": "长春", "HRB": "哈尔滨", "SHE": "沈阳",
    "NBO": "宁波", "WUX": "无锡", "ZUH": "珠海",
    "SWA": "汕头", "LXA": "拉萨", "XNN": "西宁",
    "YNJ": "延吉", "JZH": "九寨沟",

    # 港澳台
    "HKG": "香港", "MFM": "澳门", "TPE": "台北",
    "KHH": "高雄", "RMQ": "台中",

    # 亚洲热门
    "TYO": "东京", "NRT": "东京", "HND": "东京",
    "OSA": "大阪", "KIX": "大阪", "ITM": "大阪",
    "SEL": "首尔", "ICN": "首尔", "GMP": "首尔",
    "BKK": "曼谷", "SIN": "新加坡", "KUL": "吉隆坡",
    "MNL": "马尼拉", "SGN": "胡志明", "HAN": "河内",
    "JKT": "雅加达", "CGK": "雅加达", "DPS": "巴厘岛",
    "RGN": "仰光", "PNH": "金边",
    "DXB": "迪拜", "AUH": "阿布扎比", "DOH": "多哈",
    "DEL": "德里", "BOM": "孟买", "CCU": "加尔各答",
    "ISB": "伊斯兰堡", "KHI": "卡拉奇", "MLE": "马累",
    "CMB": "科伦坡", "DAC": "达卡",

    # 中东/非洲
    "JED": "吉达", "RUH": "利雅得", "AMM": "安曼",
    "CAI": "开罗", "ADD": "亚的斯亚贝巴", "NBO": "内罗毕",
    "JNB": "约翰内斯堡", "CPT": "开普敦",

    # 欧洲
    "LON": "伦敦", "LHR": "伦敦", "LGW": "伦敦",
    "PAR": "巴黎", "CDG": "巴黎", "ORY": "巴黎",
    "FRA": "法兰克福", "MUC": "慕尼黑", "BER": "柏林",
    "AMS": "阿姆斯特丹", "BRU": "布鲁塞尔", "MAD": "马德里",
    "FCO": "罗马", "MIL": "米兰", "VIE": "维也纳",
    "ZRH": "苏黎世", "GVA": "日内瓦", "CPH": "哥本哈根",
    "STO": "斯德哥尔摩", "OSL": "奥斯陆", "HEL": "赫尔辛基",
    "IST": "伊斯坦布尔", "ATH": "雅典", "MOW": "莫斯科",

    # 大洋洲
    "SYD": "悉尼", "MEL": "墨尔本", "BNE": "布里斯班",
    "AKL": "奥克兰", "WLG": "惠灵顿", "PER": "珀斯",

    # 北美
    "NYC": "纽约", "JFK": "纽约", "LGA": "纽约", "EWR": "纽约",
    "LAX": "洛杉矶", "SFO": "旧金山", "ORD": "芝加哥",
    "YVR": "温哥华", "YYZ": "多伦多", "YUL": "蒙特利尔",
    "SEA": "西雅图", "IAH": "休斯顿", "DFW": "达拉斯",
    "BOS": "波士顿", "MIA": "迈阿密", "ATL": "亚特兰大",

    # 中文名称反向映射
    "北京": "BJS", "上海": "SHA", "广州": "CAN", "深圳": "SZX",
    "成都": "CTU", "重庆": "CKG", "杭州": "HGH", "南京": "NKG",
    "武汉": "WUH", "西安": "XIY", "昆明": "KMG", "丽江": "LJG",
    "大理": "DLY", "三亚": "SYX", "海口": "HAK", "桂林": "KWL",
    "澳门": "MFM", "香港": "HKG", "东京": "TYO", "首尔": "SEL",
    "大阪": "OSA", "曼谷": "BKK", "新加坡": "SIN", "台北": "TPE",
    "厦门": "XMN", "吉隆坡": "KUL", "马尼拉": "MNL", "迪拜": "DXB",
    "伊斯坦布尔": "IST", "开罗": "CAI", "内罗毕": "NBO",
    "约翰内斯堡": "JNB", "伦敦": "LON", "巴黎": "PAR",
    "法兰克福": "FRA", "悉尼": "SYD", "墨尔本": "MEL",
    "纽约": "NYC", "洛杉矶": "LAX", "旧金山": "SFO",
    "青岛": "TAO", "天津": "TSN", "长沙": "CSX", "郑州": "CGO",
    "乌鲁木齐": "URC", "兰州": "LHW", "银川": "INC", "呼和浩特": "HET",
    "南宁": "NNG", "南昌": "KHN", "福州": "FOC", "大连": "DLC",
    "石家庄": "SJW", "太原": "TYN", "烟台": "YNT", "济南": "TNA",
    "长春": "CGQ", "哈尔滨": "HRB", "沈阳": "SHE", "宁波": "NBO",
    "无锡": "WUX", "珠海": "ZUH", "汕头": "SWA", "拉萨": "LXA",
    "西宁": "XNN", "高雄": "KHH", "胡志明": "SGN", "河内": "HAN",
    "雅加达": "JKT", "巴厘岛": "DPS", "仰光": "RGN", "金边": "PNH",
    "阿布扎比": "AUH", "多哈": "DOH", "德里": "DEL", "孟买": "BOM",
    "马累": "MLE", "科伦坡": "CMB", "达卡": "DAC", "吉达": "JED",
    "利雅得": "RUH", "安曼": "AMM", "亚的斯亚贝巴": "ADD",
    "开普敦": "CPT", "慕尼黑": "MUC", "柏林": "BER", "阿姆斯特丹": "AMS",
    "布鲁塞尔": "BRU", "马德里": "MAD", "罗马": "FCO", "米兰": "MIL",
    "维也纳": "VIE", "苏黎世": "ZRH", "日内瓦": "GVA", "哥本哈根": "CPH",
    "斯德哥尔摩": "STO", "奥斯陆": "OSL", "赫尔辛基": "HEL", "雅典": "ATH",
    "莫斯科": "MOW", "布里斯班": "BNE", "奥克兰": "AKL", "惠灵顿": "WLG",
    "珀斯": "PER", "温哥华": "YVR", "多伦多": "YYZ", "蒙特利尔": "YUL",
    "西雅图": "SEA", "休斯顿": "IAH", "达拉斯": "DFW", "波士顿": "BOS",
    "迈阿密": "MIA", "亚特兰大": "ATL", "芝加哥": "ORD",
}


def is_chinese(s: str) -> bool:
    """判断字符串是否包含中文"""
    for char in s:
        if '\u4e00' <= char <= '\u9fff':
            return True
    return False


def get_city_code(city_name: str) -> str:
    """获取城市代码"""
    # 如果输入已经是代码（全大写字母，长度<=3），直接返回
    if city_name.isupper() and len(city_name) <= 3:
        return city_name
    
    if city_name in CITY_CODE_MAP:
        mapped = CITY_CODE_MAP[city_name]
        # 如果映射结果不是中文（即代码），返回映射结果
        if not is_chinese(mapped):
            return mapped
        # 映射结果是中文，说明输入是代码，返回原值
        return city_name
    return city_name


def get_city_name(city_code: str) -> str:
    """获取城市名称"""
    if city_code in CITY_CODE_MAP:
        name = CITY_CODE_MAP[city_code]
        # 如果映射结果是中文，返回映射结果
        if is_chinese(name):
            return name
        # 映射结果不是中文（即代码），说明输入是中文名，返回原值
        return city_code
    return city_code


def load_drop_routes(data_file: str = None) -> dict:
    """加载扩散城市配置"""
    if data_file is None:
        data_file = os.path.join(os.path.dirname(__file__), "..", "data", "drop_routes.json")

    try:
        with open(data_file, "r", encoding="utf-8") as f:
            routes = json.load(f)

        # 构建映射字典: 支持代码和中文名两种 key
        route_map = {}
        for route in routes:
            o, d = route['o'], route['d']
            drop_cities = route.get("drop", [])
            
            # 代码格式 key (如 "BJS-SHE")
            code_key = f"{o}-{d}"
            route_map[code_key] = drop_cities
            
            # 中文名格式 key (如 "北京-沈阳")
            o_name = get_city_name(o)
            d_name = get_city_name(d)
            name_key = f"{o_name}-{d_name}"
            route_map[name_key] = drop_cities

        return route_map
    except FileNotFoundError:
        print(f"⚠️ 配置文件不存在: {data_file}", file=sys.stderr)
        return {}


def get_drop_cities(origin: str, destination: str, route_map: dict) -> list:
    """
    获取指定行程的扩散城市列表

    按配置文件中的顺序返回，顺序即为优先级
    """
    o_code = get_city_code(origin)
    d_code = get_city_code(destination)

    key = f"{o_code}-{d_code}"
    drop_data = route_map.get(key, [])

    # 转换为城市名称，保持原顺序
    return [get_city_name(c) for c in drop_data]


def run_flight_search(origin: str, destination: str, dep_date: str,
                      journey_type: str = None, transfer_city: str = None,
                      sort_type: str = "3") -> dict:
    """调用 flyai search-flight 命令"""
    cmd = ["flyai", "search-flight",
           "--origin", origin,
           "--destination", destination,
           "--dep-date", dep_date,
           "--sort-type", sort_type]

    if journey_type:
        cmd.extend(["--journey-type", journey_type])

    if transfer_city:
        cmd.extend(["--transfer-city", transfer_city])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(f"⚠️ 搜索失败: {result.stderr}", file=sys.stderr)
            return {}

        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        print(f"⚠️ 搜索超时", file=sys.stderr)
        return {}
    except json.JSONDecodeError:
        print(f"⚠️ JSON 解析失败", file=sys.stderr)
        return {}


def parse_price(price_str: str) -> float:
    """解析价格字符串"""
    if not price_str:
        return 0.0

    # 移除 ¥ 符号和其他非数字字符
    match = re.search(r'[\d.]+', price_str.replace(',', ''))
    if match:
        return float(match.group())
    return 0.0


def get_lowest_price(search_result: dict) -> tuple:
    """获取最低价格和航班信息"""
    if not search_result or search_result.get("status") != 0:
        return (float('inf'), None)

    data = search_result.get("data", {})
    items = data.get("itemList", [])

    if not items:
        return (float('inf'), None)

    # 按价格排序取最低
    lowest_item = None
    lowest_price = float('inf')

    for item in items:
        # 兼容 ticketPrice 和 adultPrice 两种字段
        price_str = item.get("ticketPrice") or item.get("adultPrice", "")
        price = parse_price(price_str)
        if price < lowest_price and price > 0:
            lowest_price = price
            lowest_item = item

    return (lowest_price, lowest_item)


def check_one_stop_connection(flight_item: dict, transfer_city: str) -> dict:
    """
    检查航班是否为 A→B→C 一段中转联程
    返回: {"valid": bool, "first_segment": dict, "second_segment": dict}

    排除情况：
    - 同一航班号的经停（第一、二航段航班号相同）- 这是经停，不是联程中转
    """
    if not flight_item:
        return {"valid": False}

    journeys = flight_item.get("journeys", [])
    for journey in journeys:
        segments = journey.get("segments", [])

        # 只接受恰好2个航段的联程（一段中转）
        if len(segments) != 2:
            continue

        first_seg = segments[0]
        second_seg = segments[1]

        # 检查第一航段的到达城市是否为经停城市（用户目的地B）
        arr_city = first_seg.get("arrCityName", "")
        arr_city_code = first_seg.get("arrCityCode", "")

        transfer_name = get_city_name(transfer_city)
        transfer_code = get_city_code(transfer_city)

        if arr_city != transfer_name and arr_city_code != transfer_code:
            continue

        # 排除同一航班号的经停（经停航班不能在中转站下机）
        first_flight_no = first_seg.get("marketingTransportNo", "")
        second_flight_no = second_seg.get("marketingTransportNo", "")

        if first_flight_no and second_flight_no and first_flight_no == second_flight_no:
            # 同一航班号，是经停航班，不是联程中转，排除
            continue

        return {
            "valid": True,
            "first_segment": first_seg,  # A→B
            "second_segment": second_seg,  # B→C
            "journey_type": journey.get("journeyType", "联程")
        }

    return {"valid": False}


def search_hidden_city_options(origin: str, destination: str, dep_date: str,
                                drop_cities: list, min_savings: float = 0) -> list:
    """搜索捡漏方案（只支持 A→B→C 一段中转）"""
    results = []

    # 1. 搜索原行程 A→B 的直达价格作为基准
    print(f"🔍 搜索原行程: {origin} → {destination} (直达)", file=sys.stderr)
    direct_result = run_flight_search(origin, destination, dep_date,
                                       journey_type="1", sort_type="3")
    base_price, base_flight = get_lowest_price(direct_result)

    if base_price == float('inf'):
        print(f"⚠️ 未找到 {origin} → {destination} 的直达航班", file=sys.stderr)
        return results

    print(f"   直达最低价: ¥{base_price}", file=sys.stderr)

    # 2. 遍历扩散城市 C，搜索 A→C 经停 B 的一段中转联程
    for drop_city in drop_cities:
        print(f"🔍 搜索捡漏: {origin} → {drop_city} (经停 {destination})", file=sys.stderr)

        # 搜索 A→C 的联程航班，要求在 B 中转
        hidden_result = run_flight_search(origin, drop_city, dep_date,
                                          journey_type="2",
                                          transfer_city=destination,
                                          sort_type="3")
        hidden_price, hidden_flight = get_lowest_price(hidden_result)

        if hidden_price == float('inf'):
            print(f"   未找到联程航班", file=sys.stderr)
            continue

        print(f"   联程价格: ¥{hidden_price}", file=sys.stderr)

        # 检查是否为 A→B→C 一段中转联程（恰好2个航段）
        connection_check = check_one_stop_connection(hidden_flight, destination)
        if not connection_check.get("valid"):
            # 检查是否因为同一航班号被排除
            journeys = hidden_flight.get("journeys", [])
            is_same_flight = False
            for journey in journeys:
                segments = journey.get("segments", [])
                if len(segments) == 2:
                    first_no = segments[0].get("marketingTransportNo", "")
                    second_no = segments[1].get("marketingTransportNo", "")
                    if first_no and second_no and first_no == second_no:
                        is_same_flight = True
                        break

            if is_same_flight:
                print(f"   ⚠️ 同一航班号经停，不是联程中转，跳过", file=sys.stderr)
            else:
                print(f"   ⚠️ 不是一段中转联程，跳过", file=sys.stderr)
            continue

        # 计算节省金额
        savings = base_price - hidden_price
        if savings <= min_savings:
            print(f"   节省 ¥{savings}，未达到阈值 ¥{min_savings}", file=sys.stderr)
            continue

        savings_percent = (savings / base_price) * 100

        # 提取航段信息
        first_seg = connection_check.get("first_segment", {})
        second_seg = connection_check.get("second_segment", {})

        results.append({
            "original_route": f"{origin} → {destination}",
            "original_price": base_price,
            "hidden_city_route": f"{origin} → {destination} → {drop_city}",
            "hidden_city_price": hidden_price,
            "drop_city": drop_city,
            "savings": savings,
            "savings_percent": round(savings_percent, 1),
            "flight_info": hidden_flight,
            "first_segment": first_seg,   # A→B 航段（用户实际乘坐）
            "second_segment": second_seg, # B→C 航段（弃掉）
            "journey_type": connection_check.get("journey_type", "联程"),
        })

        print(f"   ✅ 找到捡漏方案，节省 ¥{savings} ({savings_percent:.1f}%)", file=sys.stderr)

    # 按捡漏价格从低到高排序
    results.sort(key=lambda x: x["hidden_city_price"])

    return results


# 捡漏风险提示
HIDDEN_CITY_WARNINGS = [
    "⚠️ 行李直挂：托运行李将直挂到终点站C，无法在中转站B取出，建议只携带随身行李",
    "⚠️ 航司政策：频繁捡漏可能被航司列入黑名单，影响后续购票",
    "⚠️ 航班变动：如第一段航班取消或延误，航司可能直接安排到终点站C，无法在B下机",
    "⚠️ 返程风险：如购买往返票，后半段不乘坐会导致返程航段自动取消",
    "⚠️ 会员权益：捡漏可能导致里程积分失效或会员等级降级"
]

# 国际路线特别提醒
INTERNATIONAL_WARNINGS = [
    "⚠️ 护照要求：国际航线需持有有效护照才能购买",
    "⚠️ 签证要求：需确认目的地国家签证政策，部分国家需要提前办理签证"
]

# 国内城市列表（不含港澳台，港澳台视为国际路线）
DOMESTIC_CITIES = {
    # 国内城市
    "北京", "上海", "广州", "深圳", "成都", "重庆", "杭州", "南京",
    "武汉", "西安", "昆明", "丽江", "大理", "三亚", "海口", "桂林",
    "厦门", "青岛", "天津", "长沙", "郑州", "乌鲁木齐", "兰州", "银川",
    "呼和浩特", "南宁", "南昌", "福州", "大连", "石家庄", "太原", "烟台",
    "济南", "长春", "哈尔滨", "沈阳", "宁波", "无锡", "珠海", "汕头",
    "拉萨", "西宁", "延吉", "九寨沟", "威海",
    # 对应三字码
    "BJS", "PEK", "PKX", "SHA", "PVG", "CAN", "SZX", "CTU", "CKG", "HGH",
    "NKG", "WUH", "XIY", "KMG", "LJG", "DLY", "SYX", "HAK", "KWL", "XMN",
    "TAO", "TSN", "CSX", "CGO", "URC", "LHW", "INC", "HET", "NNG", "KHN",
    "FOC", "DLC", "SJW", "TYN", "YNT", "TNA", "CGQ", "HRB", "SHE", "NBO",
    "WUX", "ZUH", "SWA", "LXA", "XNN", "YNJ", "JZH", "WEH"
}


def is_international_route(origin: str, destination: str) -> bool:
    """判断是否为国际航线（含港澳台）"""
    o_name = get_city_name(origin)
    d_name = get_city_name(destination)

    # 如果出发地或目的地不在国内城市列表中，则为国际航线（含港澳台）
    o_domestic = origin in DOMESTIC_CITIES or o_name in DOMESTIC_CITIES
    d_domestic = destination in DOMESTIC_CITIES or d_name in DOMESTIC_CITIES

    # 一方是国内，另一方不是（含港澳台），则为国际
    if o_domestic and not d_domestic:
        return True
    if d_domestic and not o_domestic:
        return True

    return False


def format_output(origin: str, destination: str, dep_date: str, results: list) -> str:
    """格式化输出结果"""
    if not results:
        return json.dumps({
            "status": 0,
            "message": "未找到更低价的捡漏方案",
            "data": {
                "origin": origin,
                "destination": destination,
                "dep_date": dep_date,
                "options": []
            }
        }, ensure_ascii=False)

    # 为每个选项添加展示格式
    for opt in results:
        first_seg = opt.get("first_segment", {})
        second_seg = opt.get("second_segment", {})

        # 提取航班信息
        first_flight = first_seg.get("marketingTransportNo", "")
        first_dep_time = first_seg.get("depDateTime", "")
        first_arr_time = first_seg.get("arrDateTime", "")
        first_dep_city = first_seg.get("depCityName", "")
        first_arr_city = first_seg.get("arrCityName", "")
        first_airline = first_seg.get("marketingTransportName", "")

        second_flight = second_seg.get("marketingTransportNo", "")
        second_dep_time = second_seg.get("depDateTime", "")
        second_arr_time = second_seg.get("arrDateTime", "")
        second_dep_city = second_seg.get("depCityName", "")
        second_arr_city = second_seg.get("arrCityName", "")
        second_airline = second_seg.get("marketingTransportName", "")

        # 格式化时间（只取时分）
        def format_time(dt):
            if not dt:
                return ""
            # 格式: 2026-04-10 21:00:00 -> 21:00
            parts = dt.split(" ")
            if len(parts) >= 2:
                return parts[1][:5]
            return dt

        # 生成展示格式（使用删除线标记不飞的航段）
        display_format = {
            "route": f"{origin} → {destination} → ~~{opt['drop_city']}~~",
            "first_leg": {
                "airline": first_airline,
                "flight_no": first_flight,
                "route": f"{first_dep_city} → {first_arr_city}",
                "dep_time": format_time(first_dep_time),
                "arr_time": format_time(first_arr_time),
                "note": "乘坐"
            },
            "second_leg": {
                "airline": second_airline,
                "flight_no": second_flight,
                "route": f"{second_dep_city} → {second_arr_city}",
                "dep_time": format_time(second_dep_time),
                "arr_time": format_time(second_arr_time),
                "note": "不飞"
            },
            # Markdown 表格格式
            "table_row": {
                "route": f"{origin}→{destination}→~~{opt['drop_city']}~~",
                "price": f"¥{opt['hidden_city_price']}",
                "savings": f"¥{opt['savings']} ({opt['savings_percent']}%)",
                "flight1": f"{first_flight} {format_time(first_dep_time)}-{format_time(first_arr_time)}",
                "flight2": f"~~{second_flight}~~"
            }
        }
        opt["display_format"] = display_format

    # 生成表格数据
    table_data = []
    for opt in results:
        df = opt.get("display_format", {})
        tr = df.get("table_row", {})
        table_data.append({
            "route": tr.get("route", ""),
            "price": tr.get("price", ""),
            "savings": tr.get("savings", ""),
            "flight1": tr.get("flight1", ""),
            "flight2": tr.get("flight2", ""),
            "jump_url": opt.get("flight_info", {}).get("jumpUrl", "")
        })

    # 判断是否为国际航线，添加相应提醒
    is_intl = is_international_route(origin, destination)
    warnings = HIDDEN_CITY_WARNINGS.copy()
    if is_intl:
        warnings.extend(INTERNATIONAL_WARNINGS)

    output = {
        "status": 0,
        "message": f"找到 {len(results)} 个捡漏方案",
        "data": {
            "origin": origin,
            "destination": destination,
            "dep_date": dep_date,
            "is_international": is_intl,
            "base_price": results[0]["original_price"],
            "options": results,
            "table": table_data,
            "warnings": warnings
        }
    }

    return json.dumps(output, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="捡漏搜索工具")
    parser.add_argument("--origin", required=True, help="出发城市（名称或代码）")
    parser.add_argument("--destination", required=True, help="目的地城市（名称或代码）")
    parser.add_argument("--dep-date", required=True, help="出发日期 (YYYY-MM-DD)")
    parser.add_argument("--min-savings", type=float, default=0, help="最低节省金额阈值（元）")
    parser.add_argument("--data-file", help="自定义扩散城市配置文件路径")
    parser.add_argument("--expand-cities", help="手动指定扩散城市（逗号分隔）")

    args = parser.parse_args()

    # 加载扩散城市配置
    route_map = load_drop_routes(args.data_file)

    # 获取扩散城市列表
    if args.expand_cities:
        drop_cities = [c.strip() for c in args.expand_cities.split(",")]
    else:
        drop_cities = get_drop_cities(args.origin, args.destination, route_map)

    if not drop_cities:
        print(f"⚠️ 未配置 {args.origin} → {args.destination} 的扩散城市", file=sys.stderr)
        print(json.dumps({
            "status": 1,
            "message": "未配置该行程的扩散城市",
            "data": None
        }, ensure_ascii=False))
        return 1

    print(f"📋 扩散城市: {drop_cities}", file=sys.stderr)

    # 执行捡漏搜索
    results = search_hidden_city_options(
        args.origin,
        args.destination,
        args.dep_date,
        drop_cities,
        args.min_savings
    )

    # 输出结果
    print(format_output(args.origin, args.destination, args.dep_date, results))

    return 0


if __name__ == "__main__":
    exit(main())