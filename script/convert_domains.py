import requests
import yaml

def get_second_level_domain(domain):
    parts = domain.split('.')
    if len(parts) >= 2:
        return parts[-2]
    return domain

def remove_wildcard(domain):
    # 去掉通配符，只保留域名的主要部分
    return domain.replace('*.', '').replace('+.', '')

def is_subdomain(domain, blacklist):
    for blacklisted_domain in blacklist:
        if domain == blacklisted_domain or domain.endswith(f".{blacklisted_domain}"):
            return True
    return False

# 下载ChinaMax_Domain.yaml文件
china_max_url = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/ChinaMax/ChinaMax_Domain.yaml"
china_max_response = requests.get(china_max_url)
china_max_data = yaml.safe_load(china_max_response.text)

# 下载global_domains.txt文件
global_domains_url = "https://raw.githubusercontent.com/angwz/dnsmasq-conf/main/global_domains.txt"
global_domains_response = requests.get(global_domains_url)
global_domains_list = global_domains_response.text.splitlines()

# 提取payload部分并处理
payload = china_max_data.get('payload', [])
# 去掉通配符并去重
processed_payload = list(set(remove_wildcard(domain) for domain in payload))
# 排除global_domains.txt中的域名及其子域名
filtered_payload = [domain for domain in processed_payload if not is_subdomain(domain, global_domains_list)]
# 按二级域名排序
sorted_payload = sorted(filtered_payload, key=get_second_level_domain)

# 转换格式
transformed_lines = [f"server=/{domain}/119.29.29.29" for domain in sorted_payload]

# 保存到文件
output_file = "cn.conf"
with open(output_file, 'w') as f:
    f.write("\n".join(transformed_lines))
