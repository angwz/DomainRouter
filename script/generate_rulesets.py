import requests
import time
import toml

def fetch_rules(url):
    # 获取远程文件内容
    response = requests.get(url)
    response.raise_for_status()  # 如果请求失败，抛出异常
    content = response.text
    return content

def parse_rules(content):
    # 解析文件内容，提取 [Rules] 段落中的键值对
    lines = content.splitlines()
    rules = []
    matches = []
    in_rules_section = False

    for line in lines:
        if line.strip().lower() == "[rules]":
            in_rules_section = True
            continue
        if in_rules_section:
            if line.strip().startswith('[') and line.strip().lower() != "[rules]":
                break
            if line.strip() and ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                # 检查键或值是否包含逗号
                if ',' in key or ',' in value:
                    rules.append((key, value, True))
                elif key.lower() == "match":
                    matches.append((key, value))
                else:
                    rules.append((key, value, False))
    
    return rules, matches

def is_url_valid(url):
    # 检查URL的有效性，最多尝试3次，每次间隔5秒
    attempt = 0
    while attempt < 3:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return True
            elif response.status_code == 404:
                return False
        except requests.RequestException:
            pass
        attempt += 1
        time.sleep(5)
    return False

def generate_rulesets(rules, matches):
    # 定义基础URL和时间间隔
    base_url_domain = "https://raw.githubusercontent.com/angwz/DomainRouter/release/clash-domain/"
    base_url_ipcidr = "https://raw.githubusercontent.com/angwz/DomainRouter/release/clash-ipcidr/"
    base_url_classic = "https://raw.githubusercontent.com/angwz/DomainRouter/release/clash-classic/"
    interval = 21600
    rulesets = []

    for key, value, has_comma in rules:
        if not has_comma:
            # 为没有逗号的规则生成三个类型的URL
            urls = [
                (f"{base_url_domain}{key}.yaml", "clash-domain"),
                (f"{base_url_ipcidr}{key}-ipcidr.yaml", "clash-ipcidr"),
                (f"{base_url_classic}{key}-classic.yaml", "clash-classic")
            ]
            for url, url_type in urls:
                if is_url_valid(url):
                    rulesets.append({
                        "group": value,
                        "ruleset": url,
                        "type": url_type,
                        "interval": interval
                    })
                time.sleep(0.2)  # 每次请求间隔0.2秒
        else:
            # 处理包含逗号的规则
            value_parts = value.split(',', 1)
            key_parts = key.split(',', 1)
            group = value_parts[0].strip()
            no_resolve = ',no-resolve' if key.lower().startswith('geoip') and len(value_parts) > 1 and 'no-resolve' in value_parts[1].strip() else ''
            ruleset = f"[]{key}{no_resolve}"
            if ruleset.startswith('https'):
                if is_url_valid(ruleset):
                    rulesets.append({
                        "group": group,
                        "ruleset": ruleset
                    })
                time.sleep(0.2)
            else:
                rulesets.append({
                    "group": group,
                    "ruleset": ruleset
                })

    for match_key, match_value in matches:
        # 处理MATCH行
        rulesets.append({
            "group": match_value,
            "ruleset": "[]MATCH"
        })

    return rulesets

def main():
    # 主函数，负责整体流程控制
    url = "https://raw.githubusercontent.com/angwz/DomainRouter/main/my.wei"
    content = fetch_rules(url)
    rules, matches = parse_rules(content)
    rulesets = generate_rulesets(rules, matches)
    output_file = "rulesets.toml"

    toml_data = {"rulesets": rulesets}
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # 写入规则集，不添加额外空行
        toml_content = toml.dumps(toml_data)
        # 确保首尾行是内容
        toml_lines = toml_content.strip().split('\n')
        f.write('\n'.join(toml_lines))

    print(f"规则集已生成并保存到 {output_file}")

if __name__ == "__main__":
    main()
