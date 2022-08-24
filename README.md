# Clash_Rules

### 来源
 - 从 [LM-Firefly / Rules](https://github.com/LM-Firefly/Rules) 维护，规则数量最多，维护得最频繁，列表为不带短横线的list列表，需转换
 - 从 [Semporia / ClashX-Pro](https://github.com/Semporia/ClashX-Pro) 引用规则，规则数量类别多，规则数量一般
 - 从 [Loyalsoldier / clash-rules](https://github.com/Loyalsoldier/clash-rules) 引用规则，规则数量多

### [官方规则格式](https://lancellc.gitbook.io/clash/clash-config-file/rule-provider#example-of-a-rule-provider-file)
**If arule-provider file named as testproviderand behavior is domain:**
```
payload:
  - '.blogger.com'
  - '*.*.microsoft.com'
  - 'books.itunes.apple.com'
```
**If arule-provider file named as testprovider2and behavior is ipcidr:**
```
payload:
  - '192.168.1.0/24'
  - '10.0.0.0.1/32'
```
**If arule-provider file named as testprovider3and behavior is classical:**
```
payload:
  - DOMAIN-SUFFIX,google.com
  - DOMAIN-KEYWORD,google
  - DOMAIN,ad.com
  - SRC-IP-CIDR,192.168.1.201/32
  - IP-CIDR,127.0.0.0/8
  - GEOIP,CN
  - DST-PORT,80
  - SRC-PORT,7777
```

### 自定义规则
**An Example of Rules:**
```
rules:
  - DOMAIN-SUFFIX,google.com,auto
  - DOMAIN-KEYWORD,google,auto
  - DOMAIN,ad.com,REJECT
  - SRC-IP-CIDR,192.168.1.201/32,DIRECT
  - IP-CIDR,127.0.0.0/8,DIRECT
  - IP-CIDR6,2620:0:2d0:200::7/32,auto
  - GEOIP,CN,DIRECT
  - DST-PORT,80,DIRECT
  - SRC-PORT,7777,DIRECT
  - MATCH,auto
```
```
rules:
- RULE-SET,Apple,DIRECT
- RULE-SET,Facebook,🇺🇲 美国节点
- RULE-SET,Game,DIRECT
- RULE-SET,Google,🔰 节点选择
- RULE-SET,Netflix,🎥 奈飞节点
- RULE-SET,OneDrive,🇺🇲 美国节点
- RULE-SET,TikTok,🇯🇵 日本节点
- RULE-SET,WeChat,DIRECT
- RULE-SET,YouTube,🔰 节点选择

- RULE-SET,Adobe,DIRECT
- RULE-SET,Amazon,🔰 节点选择
- RULE-SET,GitHub,🔰 节点选择
- RULE-SET,Microsoft,DIRECT
- RULE-SET,Netease Music,DIRECT
- RULE-SET,PayPal,🔰 节点选择
- RULE-SET,Steam,DIRECT
- RULE-SET,Telegram,🔰 节点选择
- RULE-SET,Tencent,DIRECT
- RULE-SET,Twitter,🔰 节点选择
- RULE-SET,China,DIRECT


- RULE-SET,google,🔰 节点选择
- RULE-SET,icloud,DIRECT
- RULE-SET,apple,DIRECT
- RULE-SET,telegramcidr,🔰 节点选择
- RULE-SET,direct,DIRECT
- RULE-SET,cncidr,DIRECT,no-resolve
- RULE-SET,lancidr,DIRECT,no-resolve
- RULE-SET,applications,DIRECT
- RULE-SET,tld-not-cn,🔰 节点选择
- RULE-SET,greatfire,🔰 节点选择
- RULE-SET,gfw,🔰 节点选择
- RULE-SET,proxy,🔰 节点选择
- MATCH,🔰 节点选择
```
**[GeoIP数据库](https://github.com/Hackl0us/GeoIP2-CN/tree/master)**
```
# ... 省略其他规则 ...
GEOIP, CN, DIRECT # 👀 建议在这里使用规则
FINAL, PROXY # ⬇️ 最终规则
```

> 手动维护...
