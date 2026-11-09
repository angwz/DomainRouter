# DomainRouter v2 实施规范 · 产物、兼容、验证与 CLI

版本：1.5 · 日期：2026-11-08 · 第 11～14 节

本分册与入口索引列出的其他三份分册共同构成完整规范，必须顺序阅读；本文件不是单独的需求摘要。

[返回规范入口](../v2-implementation-spec.md)

<a id="outputs"></a>

## 11. 配置、产物和命名

### 11.1 输入与计划目录

以下目录是实施目标，不是当前已存在的实现：

```text
my.wei                              # 保留用户的主要输入
subconverter_config/groups.toml      # 默认策略组源，迁移前不覆盖
config/domainrouter_v2.toml          # v2 构建选项，实施时新增
config/clash-base.yaml               # 用户显式提供的完整基础设置；私有文件不提交
examples/minimal/                   # 可分发、无凭据、无联网来源的完整演示配置
sources.lock.json                   # 来源内容与解析选项锁，不包含原始对象本身
.cache/domainrouter_v2/objects/      # 默认本地对象缓存，不提交、不发布
config/mihomo-compiler.lock.json     # 受支持工具目标及下载校验信息
src/domainrouter_v2/                 # 核心包
tests/                              # 合成数据、固定快照、回归与适配器
docs/v2-implementation-spec.md       # 规范入口索引
docs/v2/01-foundations-and-input.md  # 第 0～6 节
docs/v2/02-engine-and-algorithms.md   # 第 7～10 节
docs/v2/03-artifacts-and-verification.md # 第 11～14 节
docs/v2/04-delivery-and-handoff.md    # 第 15～19 节
docs/claude-code-start.md            # 可直接粘贴的短启动提示
dist/                               # 构建目录，默认不提交到 main
  clash-domain/<id>.mrs
  clash-ipcidr/<id>-ipcidr.mrs
  clash-classic/<id>-classic.yaml
  groups.toml
  rulesets.toml
  provider-overrides.yaml            # 仅 provider 格式和名称的桥接片段
  clash-base.yaml                    # 基础设置与桥接片段合并后的完整 base
  external-config.toml               # 同 generation 的完整 subconverter 导入入口
  manifest.json
  reports/build.json
  reports/build.md
build/readable/                      # 不默认发布的可读中间资料
  clash-domain/<id>.yaml
  clash-ipcidr/<id>-ipcidr.yaml
build/packages/                      # Python wheel/sdist，与规则产物分开
```

默认沿用三类目录名；domain/ipcidr 后缀改为 `.mrs`，classical 仍为 `.yaml`。`classical` 是内核行为名，`clash-classic` 是发布目录和 subconverter 类型名，两者不能混淆。`build/readable` 是调试目录，不受“最多三个发布规则资源”的数量约束，也不应被订阅引用。

构建配置至少包括：输入路径、输出根目录、发布基础 URL、来源锁文件、默认 IP 策略、允许空合集、快照陈旧规则、目标版本/摘要和分析资源限制。核心模块不硬编码 angwz 或 GitHub 仓库地址。

合集名与 artifact ID 分开。现有无冲突的安全 ASCII 名称可沿用；首选候选仅允许 `[A-Za-z0-9][A-Za-z0-9_-]{0,63}`。Windows 保留设备名、尾点/空格、大小写折叠碰撞或不满足候选语法的名称，使用 `c-` 加原合集名 UTF-8 SHA-256 的固定前 20 个十六进制字符作为 fallback，清单记录映射。fallback 冲突时扩展到完整哈希，仍冲突则失败，绝不按平台随机加序号。

还必须全局校验三个 behavior 的文件 stem 以及重复引用后 fork 生成的真实 provider 名，不能只检查同一输出目录：例如合集 `Example-ipcidr` 的 domain 文件可能与 `Example` 的 ipcidr provider 同名；`Example_2` 可能与重复引用的名称冲突。冲突涉及的资源统一改用含 behavior 与上述哈希的安全 stem，再重新规划全部 ProviderBinding；迭代直到名称唯一或明确失败。规划与哈希选择只依赖完整输入、固定规则和语义版本，禁止依赖并发先到先得。用户原有 base provider 的占用按第 12 节报错，不自动接管。

最小构建配置契约如下。字段名属于实施规范；示例中的发布地址可被 fork 用户替换，不能写死在引擎中。实际验证目标另需补充版本/二进制摘要及测试环境配置。

```toml
schema_version = 2
project_root = ".."

[paths]
rules = "my.wei"
groups = "subconverter_config/groups.toml"
sources_lock = "sources.lock.json"
cache = ".cache/domainrouter_v2"
clash_base = "config/clash-base.yaml"

[output]
directory = "dist"
base_url = "https://raw.githubusercontent.com/YOUR_OWNER/domainrouter_v2/release"
generation_prefix = "v2"
interval_seconds = 21600
domain_format = "mrs"
ipcidr_format = "mrs"
classical_format = "yaml"
publish_readable = false

[mrs]
compiler = "tools/mihomo"
compiler_target = "config/mihomo-compiler.lock.json"

[converter_bridge]
mode = "base-preseed"

[policy]
target_ip_no_resolve = true
allow_empty_collections = []

[fetch]
max_workers = 8
max_attempts = 3
connect_timeout_seconds = 10
read_timeout_seconds = 30
total_timeout_seconds = 120
max_response_bytes = 33554432
allow_stale = false
max_stale_seconds = 604800

[verification]
require_integration_for_publish = true
subconverter_commit = "a33d49e4c6702681a0599add8ecbeedfb5c5a8c0"
targets = "config/verification-targets.lock.json"
```

顶层 `project_root` 以配置文件所在目录为基准解析，默认 `..`；示例即仓库根。结果写入有效配置报告，其余相对路径均以此根解析，不能从调用工作目录推测。未知字段、非正数限制、冲突路径与不支持的策略值必须校验。

`YOUR_OWNER` 是发布配置占位符，正式 build/publish 必须要求替换。公开最小示例使用单独的、已明确标注为本地演示的配置，base_url 可设为 `http://127.0.0.1:18080`，build 不需要服务已启动，verify 再使用第 12.3 节的测试地址映射；用户迁移配置填写 `angwz` 和实际发布路径。不能为让演示成功创建或推送一个远端仓库。base_url 通过 URL 结构解析后追加受控 generation/path，禁止 userinfo、查询和 fragment；不能用不受控字符串拼接 URL。普通发布只接受已配置的 HTTP/HTTPS 资源地址，不把工具/输入路径当 URL。

`tools/mihomo` 是示例受控工具路径，Windows 可配置为实际 `.exe`。`compiler_target` 必须包含 schema_version、版本、源码 ref（可取得时）、按 OS/arch 区分的官方获取 URL、归档 SHA-256、解压后可执行文件 SHA-256、归档内路径和许可证来源。工具准备命令显式选择本机目标、下载/校验并防止解压路径逃逸；build 只校验并使用已准备工具，不下载最新版。工具文件的本地路径可以不同，内容摘要决定目标。

`verification-targets.lock.json` 对内核、转换器二进制或镜像、测试数据记录版本、源码提交、二进制 SHA-256/镜像 digest、平台和能力；不能只写一个源码 commit 就代表运行程序已固定。相同编译/客户端版本是首版默认，矩阵扩展必须有实际验证。首版格式配置只接受上面的组合；`require_integration_for_publish` 必须为 true，不能靠关闭它发布未验收产物。

无来源的纯本地工程使用显式空来源锁，也必须可离线重建。没有 clash_base 时，check 可完成规则部分并报告桥接未就绪；正式 build 必须有完整 base（用户输入或显式选择的非敏感示例），否则失败，不生成看似完整的接入包。预览/check 与正式 build 的状态不能混为一谈。

输出根不得是项目根、输入文件的祖先、缓存根或源码目录；拒绝 `..` 逃逸、危险符号链接及覆盖输入的冲突。临时构建与目标输出在可原子替换的受控位置，Windows 文件占用失败时保留上次成功包并明确报错。`--out` 只改变物理落盘位置，不改变发布 URL。

### 11.2 可读序列化与 MRS 编译

- 可读 YAML 内容只有合法 provider payload 和稳定说明信息；条目全部作为字符串序列化。
- 不在 payload 内写出口；出口来自引用。
- domain 中输出原生域名模式；ipcidr 中只输出网络字符串。
- classical 中参数在正确的条件位置，不能含不支持的 provider 控制语句。
- 不把当前时间写入语义产物；构建时间写报告。数量从最终有效模型计算。
- 不能对序列化后的字符串再运行域名格式化和优化，避免重复加引号、列表符号或 `+.`。

使用固定 Mihomo 的官方转换命令，以下为实施时执行的契约示例，本次文档修订未运行这些命令：

```text
mihomo convert-ruleset domain yaml build/readable/clash-domain/Example.yaml dist/clash-domain/Example.mrs
mihomo convert-ruleset ipcidr yaml build/readable/clash-ipcidr/Example-ipcidr.yaml dist/clash-ipcidr/Example-ipcidr.mrs
```

也可以从经过相同语义校验的文本中间格式转换：将第二个参数 `yaml` 改为 `text`。本项目默认使用 YAML 中间表示便于审阅。classical 不支持 MRS，不能调用上述命令强行转换。

MRS 构建要求：

1. 优化和严格输入校验先于转换；MRS 编译不是去重算法的替代。内核某些插入路径会记录警告并跳过非法条目，因此退出码为零/文件非空不能单独证明无损。
2. 显式传入 behavior 和输入格式；使用参数数组调用进程，不构造含用户内容的 shell 命令。
3. 空分区跳过，不调用编译器生成空 MRS；失败先保留临时文件，不能截断已成功发布的文件。
4. 用目标读取器加载 MRS，比较可读规范模型与加载后的匹配集合、数量解释和行为。条目计数只作辅助，不能以计数相等代替集合与边界测试。
5. 固定版本若支持 MRS 导出文本，可做语义 round-trip；导出顺序及 `精确 + 子域后缀` 的等价压缩可能变化，比较规范模型而非逐行相等。无导出能力时使用真实 reader/匹配适配器，不能跳过门禁。
6. manifest 分别记录可读模型哈希、MRS 字节哈希、behavior、format、工具版本/平台/摘要。编译器摘要是构建 ID 输入；同一受控工具/平台必须验证字节可重建，跨工具/平台不冒充字节一致。
7. MRS 是二进制资源，不追加文本注释、不按 UTF-8 修剪、不做行尾转换。文本文件的 LF/末尾换行约定不作用于 MRS。

MRS 可减少文本解析和构建索引的加载工作，但 YAML 和 MRS 都可进入相同的运行时域名/IP 集合。不得把“体积缩减 60%～80%”或“内存减少同样比例”写成保证；第 13.4 节必须分别测文件体积、加载耗时、加载峰值和稳态内存。

### 11.3 rulesets.toml

遍历 `[Rules]` 的 RouteEntry，按 OutputPlan 生成 `[[rulesets]]`，使用本次本地清单决定哪些文件存在。禁止通过请求已发布 URL 的 200/404 决定本次应输出什么。

普通引用的类型继续使用 fork 已支持的 `clash-domain`、`clash-ipcidr`、`clash-classic`，其 URL 分别指向 MRS、MRS、YAML。这里的 type 表示路由行为分类，不是 Mihomo 的 format；format 由第 12 节桥接写入。不能凭空发明未被 fork 识别的 `clash-domain-mrs` 等类型，不能指望 TOML 里追加一个会被旧 binding 忽略的 format 字段解决问题。

`group` 为准确目标名，`ruleset` 为资源 URL，默认更新间隔沿用 21600 秒并可配置。目标、类型、URL、参数分别建模，不把未知字段塞进名称。

内联示例的期望结构：

```toml
[[rulesets]]
group = "DIRECT"
ruleset = "[]GEOIP,CN,no-resolve"

[[rulesets]]
group = "🐳 漏网の鱼"
ruleset = "[]MATCH"
```

原生 ipcidr 的外层 `no-resolve` 由用户 fork 生成；DomainRouter 必须在验收时检查，不能通过把 `,no-resolve` 塞入 group 名称来“修好”。需要额外转换适配时，应形成独立、可验证的后端，而非污染通用数据模型。

普通合集三类引用的期望示例如下；实际 URL 用已计算的构建 ID 替换 `GENERATION`，没有相应文件时不生成该项：

```toml
[[rulesets]]
group = "🌠 节点选择"
ruleset = "https://raw.githubusercontent.com/angwz/domainrouter_v2/release/v2/GENERATION/clash-domain/Example.mrs"
type = "clash-domain"
interval = 21600

[[rulesets]]
group = "🌠 节点选择"
ruleset = "https://raw.githubusercontent.com/angwz/domainrouter_v2/release/v2/GENERATION/clash-ipcidr/Example-ipcidr.mrs"
type = "clash-ipcidr"
interval = 21600

[[rulesets]]
group = "🌠 节点选择"
ruleset = "https://raw.githubusercontent.com/angwz/domainrouter_v2/release/v2/GENERATION/clash-classic/Example-classic.yaml"
type = "clash-classic"
interval = 21600
```

### 11.4 groups.toml

策略组源继续采用 subconverter 可理解的 TOML 定义，默认读取现有 `subconverter_config/groups.toml`，规范化后写入 dist，不覆盖输入文件。

- 校验唯一名称、目标内置组白名单、`[Rules]` 引用和组间引用。
- 检查引用循环和不存在的引用。允许前向引用。
- 保留组内选择/回退顺序，不按字典序排序节点或引用。
- 节点名称正则按 subconverter 的真实引擎验证，不假定 Python re 完全等价。
- 名称不能含目标 fork 无法无损表达的逗号、换行等分隔符；外围引号不能被视为可以自动修复 fork 输出词法的手段。需要这类名称时先报兼容错误，不在生成时擅自改名。
- 类型、健康检查地址、间隔、lazy、筛选表达式等保持用户定义，不从合集名称自动推断。
- 测试使用合成节点验证“匹配到节点”“没有节点”“回退”“UDP 能力”等情况；不需要真实机场凭据。

### 11.5 manifest 与解释报告

确定性清单至少包含语义/工具版本、输入哈希、来源快照哈希、项目参数、目标环境标识、各产物路径/类型/条数/哈希、route 序号与引用及确定性诊断计数。验证执行状态只放运行报告，不在同一 manifest 中既随运行改变又承诺字节重建。

每个资源同时记录 behavior 和 format，不能从 `.yaml`/`.mrs` 或目录名猜运行配置。ProviderBinding 记录 fork 名称映射和所需 `format`；清单还记录完整 base 与 provider 覆盖片段的哈希。

构建的确定性标识由原始输入、规范化配置、来源快照、语义/计划/后端版本、引擎代码指纹、运行时依赖标识、解释器/Unicode 环境标识、编译工具摘要、基础配置输入、相关地理数据摘要和目标能力计算，不包含墙上时钟、抓取时间、验证执行状态或缓存命中状态。来源锁中的内容哈希和解析设置参与构建 ID；retrieved_at、ETag 等非语义元数据不参与，避免相同内容重新抓取就更换 generation。锁定文件完整字节摘要可另作审计记录，不能误用作决定语义构建 ID 的唯一输入。

引擎版本号不能代替代码指纹：源码 checkout 对实际包内源码及影响行为的资源计算内容摘要，工作区改动也必须反映；安装包按相同包相对路径与内容计算，并记录包版本。Git commit 可另作审计记录，不代替内容指纹，也不因仅文档提交变化就更换 generation。记录实际运行的 Python 实现/版本、运行时依赖版本与内容标识，特别是 idna/Unicode 数据；不能在同一 generation 下换一套规范化实现。指纹收集排除绝对安装路径、mtime、__pycache__ 和仅文档/开发测试文件。缺少 Git 元数据的 wheel 安装也必须能得到指纹，不能要求使用者克隆仓库才能运行。

这里的规范化配置只包含会影响语义/产物的值：本地绝对项目根、缓存位置、临时目录、工具本地路径不进入语义 ID；工具摘要、影响行为的配置和发布基础 URL 进入。确定性清单中的输入位置使用项目相对路径或稳定资源 ID，绝对运行路径只放运行报告。移动本地目录不应仅因路径大小写或机器不同改变 URL 规划。

构建 ID 的版本化输入表示使用 UTF-8 的规范 JSON：键按 Unicode 码点排序、无额外空白、字符串不做全局 Unicode 规范化、仅允许字符串/整数/布尔/null/数组/对象，不含浮点；数组按已定义语义顺序。文件位置用项目相对 POSIX 路径或稳定资源 ID。对该字节序列计算 SHA-256，generation 默认使用完整十六进制值。实现必须保存脱敏的输入字段清单以便复核；私有凭据值不进入公开 JSON，实际响应由内容哈希锁定。

运行时间、耗时、完整审计锁哈希和验证执行状态放在运行报告。manifest 的确定性部分与运行状态分开；产物目录中 reports 可以每次变化，不属于逐字节重建断言对象。验证报告记录 generation、manifest 摘要、验证过的产物哈希和验证目标；发布器检查对应关系，不能把旧报告复制给新产物。manifest 不包含自己的哈希，也不把运行报告作为构建 ID 输入，避免自引用。

每条有效输入必须可归入：输出、明确修复后输出、重复合并、被覆盖、参与精确合并、明确忽略、错误未发布之一。不能只写一个总删除数。

覆盖链最终指向仍然存在的代表规则或有记录的合并结果。不能把已经删除的覆盖者作为解释链终点。

<a id="compatibility"></a>

## 12. subconverter 兼容门禁

核心验收必须覆盖用户 fork 固定提交，而不是只测试上游。测试应启动隔离实例和本地静态产物服务，使用无凭据合成节点及测试外部配置。

### 12.1 首版 MRS 格式桥接：base-preseed

固定 fork 在原生 provider 生成时写入 type、behavior、url、path、interval，但不主动输出 format，也不清空已有节点的其他字段。首版据此采用以下配置接法，而不是要求先改服务源码：

1. 根据完整 RouteEntry 序列和 fork 的实际 `findFileName`/去重命名算法生成 ProviderBinding。重复引用的 `_2`、`_3` 等名称也要覆盖，不能只按合集名猜一个名称。
2. 生成 `provider-overrides.yaml`，只包含准确名称对应的 format；domain/ipcidr 为 mrs，classical 为 yaml。例：

```yaml
rule-providers:
  Example:
    format: mrs
  Example-ipcidr:
    format: mrs
  Example-classic:
    format: yaml
```

3. 使用安全的 YAML 结构合并，把该片段写入用户显式提供的完整基础配置，得到本 generation 的 `clash-base.yaml`。不能把只有 format 的片段单独当完整 Clash 配置，更不能覆盖现有 fake-ip/DNS/入站设置。与用户其他 provider 同名时先报 `E_PROVIDER_NAME_COLLISION`，不静默接管。
4. 测试外部配置/生产接入配置的 `clash_rule_base` 必须使用同一 generation 的完整 base；同时使用同 generation 的 groups/rulesets。调用正常 rule、原生 provider 生成路径。
5. fork 补充其他字段后，验证最终节点仍保留预置的 `format`。基于源码的字段保留推断只有经实际版本转换才算兼容通过。

旧 fork 可能把客户端本地缓存 path 仍命名成 `.yaml`。Mihomo 按显式 format 选择 reader，因此该缓存后缀本身不决定文件格式；首版允许保留该后缀，条件是实际目标版本的 MRS 加载通过验收，不为改缓存后缀先修改服务代码。远端发布资源和实际内容必须是 `.mrs` 与 MRS。

完整 base 只有在明确作为可公开配置、且不含控制器 secret/认证等敏感字段时才进入公开发布；含敏感字段的生产设置保持在 VPS 私有 base 中，在同一结构化合并步骤接入公开覆盖片段。私有 base 的具体接法同样需真实验证，不能把“公开片段存在”当作生产已接入。源 base 不存在时，隔离测试用显式的非敏感 fixture 完成 M3，实际生产接入留在 M4b；不阻塞 M4a 的本地交付。

不能依赖 `.mrs` 后缀触发自动识别，也不能只在当前 CLI 输出后手工修改一次订阅。桥接属于每次订阅生成的完整配置路径。若实际版本会清空预置字段，首版门禁失败并给出最小复现；后续可单独选择 fork 的 format 透传扩展或明确的每次转换后处理适配器，不能静默采用另一后端或退回 YAML。本项目本轮仍不在 subconverter 仓库编码。

### 12.2 必须证明的转换结果

必须证明：

1. 组定义、rulesets、同 generation 的 base 与三类发布资源（MRS/MRS/YAML）能通过实际配置接法一起使用。
2. 最终配置处于正常 rule 模式，包含预期 provider，未退回不等价的展开或脚本模式。
3. provider 的 behavior、format、资源 URL、路径、更新间隔与 ProviderBinding/清单一致；MRS URL 不得以默认 yaml 格式读取。
4. ipcidr 外层 `RULE-SET` 的目标和 `no-resolve` 位置正确，未重复添加。
5. 三类引用在 `[Rules]` 对应位置连续排列；内联 GEOIP 与 MATCH 保持位置和语义。
6. 精确、`.suffix`、`+.suffix`、一级及中间通配经可读模型 → MRS → 最终 provider 保真；复杂 classical 仍为 YAML 且未被旧类型筛选丢弃。
7. 重复引用同一文件时，转换器的 provider 命名处理不会导致错误引用；比对时允许转换器合法重命名，但必须验证名称到内容/目标的映射。
8. 不存在的组、未加载资源、格式不符、缓存错误页或转换器静默省略，能够使门禁失败。
9. 重复引用对应的所有 provider 格式都正确；更换 generation 后不沿用旧 format 或错误内容的缓存。桥接合并没有修改 DNS、fake-ip、组内顺序或其他基础设置。

实施时确定并记录产生该路径所需的实际参数，包括 `expand`、`script`、`managed_config_prefix`、外部配置和 rule generator 选项。不能把任意参数值写成未验证的万能设置。

集成契约至少要求启用规则生成、覆盖原基础配置的顶层路由、关闭节点列表/脚本模式，并实际进入原生 provider 生成分支。预期使用 `enable_rule_generator=true`、`overwrite_original_rules=true`，请求 `script=false`、`expand=false`，但仍须核验实际版本的路径条件。基础配置中的旧 rules 必须被明确接管并提示；DNS、fake-ip、入站和无关设置保留。不能一边承诺 `[Rules]` 是唯一顺序，一边把旧 base rules 隐式前置。

对带逗号/括号等字符的正则和复杂内联输入，v2 能解析原文不等于 fork 或 Mihomo 能无损接受同一输出词法。不存在可靠输出表示时必须报 `E_BACKEND_LOSSY`，不得自行发明 CSV 引号或字符串转义后宣称兼容。

固定内核的 `ParseRulePayload` 对 DOMAIN-REGEX/逻辑等类型有专门的逗号重组规则，同时会 trim 分段空格。后端测试必须比较实际解析得到的 payload/AST 与模型，例如正则字符类中逗号后的空格不能悄悄丢失。能无损处理的逗号允许保留，不一概拒绝；无法无损处理的组合给出具体错误。

若 VPS 实际版本和固定提交不同，先对该部署版本运行相同用例，再给出支持结论。本项目的首次实施不需要修改或重建用户的 VPS 服务；需要服务变更时，先提供具体差异和失败用例。

### 12.3 完整入口与隔离地址

首版必须生成 `external-config.toml`，不能只留下三个互不关联的配置片段。对可公开完整 base 的默认接法，结构如下；`GENERATION` 替换为本次完整构建 ID，三处资源地址都固定到它：

```toml
version = 1

[custom]
enable_rule_generator = true
overwrite_original_rules = true
clash_rule_base = "https://raw.githubusercontent.com/angwz/domainrouter_v2/release/v2/GENERATION/clash-base.yaml"

[[custom_groups]]
import = "https://raw.githubusercontent.com/angwz/domainrouter_v2/release/v2/GENERATION/groups.toml"

[[rulesets]]
import = "https://raw.githubusercontent.com/angwz/domainrouter_v2/release/v2/GENERATION/rulesets.toml"
```

上述结构来自固定 fork 的 `loadExternalTOML`、`importItems` 和 binding；这里使用 TOML import，不把 INI 的 `!!import:` 词法混进去。导入文件本身保留各自的 `[[custom_groups]]` / `[[rulesets]]` 数组；不递归套多层 import。稳定入口可以是 `latest.toml`，但其内容只引用某个不可变 generation，不能分别引用三个可能独立刷新的 latest 文件。私有 base 场景生成的接入入口只留在本地/部署目录，并通过已验证的本地路径或私有 URL 指向同代合并 base，不能为了凑齐公开包而上传它。

本地集成验收不依赖先发布到 GitHub。启动仅用于测试的静态服务，验证器在独立工作目录把完整包的地址通过同一 URL 规划器覆盖为该服务的基址，重新生成测试用 TOML/base，之后运行隔离转换器与内核。覆盖只作用于标记为 verification-only、禁止发布的测试副本；报告分别记录生产候选 generation/manifest 哈希、测试副本哈希以及 URL 映射，不伪造“字节完全一致”。测试输出与生产候选的差异白名单仅限 URL/隔离缓存路径和测试节点/监听环境，必须结构化比对路由、format、behavior、参数和资源字节，不能把两套任意配置的成功都叫作同一候选通过。

真正离线的测试使用预先准备的内核、转换器、合成节点、地理数据和快照。若目标程序无法在现有主机运行，仍应交付复现脚本/容器定义与明确未运行状态；不能把生产账号、订阅或真实 VPS 当成本地算法验收前提。

<a id="verification"></a>

## 13. 匹配正确性与测试规范

### 13.1 三层对照

必须分别验证，不能用其中一层代替另外两层：

1. **语义变换检查**：域名语言、IP 区间等在每次变换前后相等；包含删除具有可审阅的证明类别。
2. **独立参考解释器**：对规范化后、未优化的参考计划，用简单实现求值，与优化计划比较。不能复用优化 trie 作为参考匹配器；不能仅把预期值写成实现输出。
3. **真实转换与内核对照**：未优化产物和优化产物都经过用户 fork，在同一内核、配置、节点能力及受控 DNS 条件下比较；同时分别将可读版本与其 MRS 版本对照。不能仅检查二进制能解压，不能只比较两份同时经过错误编译的结果。

参考解释器覆盖明确的标签模式、地址、端口等。正则、逻辑和目标内核特有类型使用实际内核的测试适配器作依据；不能因参考解释器暂时不支持就略过这些输出的测试。

第 9.3 节的包含公式由可审阅的推导支持；还必须用另一种直接标签匹配器和小型有限字母表的穷举矩阵交叉检查。该矩阵至少含两个互不相同的普通标签、模式中所有 literal、精确/一个 ANY/多个 ANY/中间 ANY、不同长度与无上界的代表边界，测试候选索引与全对穷举得到同一包含结论。测试解释器不调用优化器的包含公式；有限穷举是实现交叉验证，不能单独冒充对无限语言的证明。

真实目标验证可以采用固定源码的薄测试适配器，直接调用实际规则/provider reader 并注入元数据和 helper，配合进程级加载/受控请求测试。适配器只暴露测试必要接口，不复制一套目标规则算法。内核配置检查命令仅证明可加载；不能仅凭 `mihomo -t` 就认为命中、DNS 和路由行为已验收。

### 13.2 观察结果

请求测试元数据至少能表示：原始 host、用于匹配的 host、真实/未知目标 IP、fake-ip 映射状态、来源 IP、端口、TCP/UDP、进程信息及查询结果、入站元数据。

对照观察：匹配集合、最终策略组及控制流结果、匹配阶段的目标 DNS 请求、必要的元数据状态。优化后显示的首条命中规则 ID 可以变化，但必须能够解释其与原规则的等价关系。

默认 profile 的目标 IP 条件不能因为优化新增匹配阶段的 DNS 请求。已存在真实 IP 时仍允许 IP 匹配；仅有域名且没有真实 IP 时，不能为了提高 IP 命中率解析域名。

DNS 测试隔离：使用受控解析器和可计数请求，区分分流阶段查询、代理节点域名解析、DIRECT 实际拨号解析、规则资源下载解析。不能把正常拨号查询误判成优化器泄露，也不能只观察总查询数为零就声称已覆盖各种路径。

依赖地理数据的测试固定 geosite/geoip/MMDB 等实际使用文件及哈希，并记录 sniffing、进程查询模式等会影响元数据的设置。已有 `[Rules]` 中的自定义地理标识，必须在该数据快照中存在；不能用另一个数据库的偶然结果替代。

### 13.3 必须覆盖的回归矩阵

下列是最低要求，可根据实际实现增加数据；不能只写同名测试而没有相应断言。

| ID | 场景 | 必须验证 |
| --- | --- | --- |
| D01 | 裸 `a.hk` | 自身、一级、多级均匹配；`not-a.hk` 不匹配 |
| D02 | `'a.hk'` 与 `DOMAIN,a.hk` | 仅自身 |
| D03 | 双引号域名 | 仍使用手写默认扩展 |
| D04 | `'*.a.hk'` | 一级匹配；根和二级不匹配 |
| D05 | 裸 `*.a.hk` | 全部子级匹配；根不匹配 |
| D06 | `.a.hk` 和 `+.a.hk` | 分别验证根是否包含 |
| D07 | 精确根 + 仅子域后缀 | 合并结果等价于加号后缀 |
| D08 | 精确父域与子域 | 父域不删除子域 |
| D09 | 有限的多个子域名 | 不推导任意通配符 |
| D10 | 中间/多个 ANY 标签 | 保留层级和固定标签位置 |
| D11 | 本机输入与第三方相同文本 | 根据上下文保持不同默认含义 |
| D12 | 大小写、IDNA、FQDN 末尾点 | 手写按 authoring 策略，第三方保留或诊断；规范化后的边界经目标验证 |
| D13 | 局部标签通配、`?`、误放 `+` | 正确类型分流或明确拒绝，不擅自扩展 |
| D14 | 重复模式互相覆盖 | 至少保留一个稳定代表；不发生互删 |
| D15 | 模式中间 ANY、额外前缀、合法标签边界 | 不把模型标记输出为字面 ANY，不混用字符串通配 |
| D16 | 显式类型中带引号的 payload | 引号包装不覆盖显式类型含义 |
| D17 | 长度包含但固定标签位置不同 | 不能误判包含；索引候选与直接全对交叉验证一致 |
| D18 | 带中间 ANY 的自身 + 真子域闭包 | 精确合成对应 +. 模式，再消除新包含项；重复优化不变 |
| D19 | 单引号全 ANY 模式、自由行孤立符号 | 保留合法非空语言，歧义符号不默默成为全匹配 |
| D20 | DOMAIN-SUFFIX 的星号、加号、前导点 | 不把显式字面 payload 偷换成原生模式，给出兼容诊断 |
| I01 | 单 IPv4/IPv6 | 精确 `/32`、`/128` |
| I02 | 父网段、子网段、单 IP | 精确并集，冗余消除 |
| I03 | 两个相邻 `/25` | 精确合成 `/24` |
| I04 | 有空洞的网段 | 空洞内地址继续不匹配 |
| I05 | 网络首末及外侧地址 | 边界判断准确 |
| I06 | `/0`、最大地址、IPv6 大网段 | 无溢出、无枚举地址空间 |
| I07 | CIDR 主机位 | 规范化并报告；不误改非法输入 |
| I08 | 同值的来源与目标条件 | 不合并、不进错误分区 |
| I09 | mapped IPv6、非法 zone/前缀 | 按目标语义处理或诊断 |
| P01 | 注释、列表、中文引号、外包装 | 修复不改变精确/后缀语义 |
| P02 | 正则中的方括号、冒号、逗号 | 不误拆节、字段或注释 |
| P03 | IPv6 内联规则 | 正确识别策略分隔符 |
| P04 | payload 引号、非法 YAML、重复键 | 正确语义或明确错误，无危险构造 |
| P05 | 带原出口和参数的来源 | 正确提取条件，保留参数并记录出口剥离 |
| P06 | `@source` 与 `@site` | 下载与主机提取分开；失败不自动互换 |
| P07 | auto 格式有歧义 | 要求指定格式，不凭扩展名猜测 |
| P08 | MATCH/引用语句混入合集 | 不偷偷忽略或输出成 provider 成员 |
| P09 | 完整配置显式 exclude_types | 仅排除声明的 MATCH/FINAL 并报告；无声明则报错 |
| P10 | 合集引用附加 src/no-resolve、逗号名称 | 拒绝未支持的引用参数或无法由 fork 表达的名称 |
| P11 | 显式/隐式粘贴块及后续节 | 缩进、结束标记和上下文切换准确，缺结束不吞后续输入 |
| P12 | YAML 布尔/null/数值条目、别名和自定义 tag | 明确拒绝，不转换成貌似有效规则，不展开危险结构 |
| P13 | 正则中的字面引号及无法序列化的逗号 | 保留正则内容；后端不能表达时明确失败 |
| R01 | AI 特例在前、Google 后缀在后 | 特例优先，跨合集不删除 |
| R02 | 多合集和三类文件 | 原始 route 次序、连续区块正确 |
| R03 | 内联 GEOIP 穿插、末尾 MATCH | 保留位置、目标和参数 |
| R04 | 重复合集引用、未引用合集 | 不擅自去重引用，独立产物完整 |
| R05 | 相同输入的并发完成顺序变化、纯集合成员重排 | 调度不改变计划；纯集合重排不改变集合，效果成员保持已定义来源顺序 |
| R06 | UDP 不支持、PASS 等继续匹配 | 与实际内核控制流一致；未支持时明确拒绝对应能力 |
| E01 | AND/OR/NOT | 不展平成并集，保持短路和叶节点参数 |
| E02 | 域名/进程/地址等混合 classical | 重排没有改变结果和必要元数据行为 |
| E03 | 复杂正则 | 使用目标引擎，不以 Python re 验证兼容 |
| E04 | 相同 classical 条件跨效果屏障 | 不因语义键相同就移动/删除；屏障求值行为保留 |
| N01 | fake-ip 已映射、目标 IP 未知 | 域名规则可用；IP 条件不主动解析 |
| N02 | 已有真实目标 IP | no-resolve IP 条件仍可匹配 |
| N03 | 前面已有解析结果 | 不把 no-resolve 误解为拒绝已有结果 |
| N04 | 复合条件里的目标 IP | 参数应用到正确叶节点 |
| N05 | DNS 失败、不同答案 | 不能靠真实公网偶然结果通过测试 |
| N06 | target_ip_no_resolve=false | 首版配置明确拒绝，不能与强制补参数的 fork 冲突 |
| N07 | 未知 IP、no-resolve 与 NOT | 保持叶节点及否定结果，不擅自补 DNS 或当作整条不匹配 |
| B01 | 相同锁文件重复构建 | 语义产物逐字节相同 |
| B02 | 重复优化 | 同一版本优化幂等 |
| B03 | 来源失败、旧快照、空响应、HTML | 明确状态，不能错误发布空规则 |
| B04 | 命名碰撞、不存在的组、循环 | 构建明确失败，保留上次产物 |
| B05 | 原生必需包含与可选复杂分析的资源限制 | 原生包含不因分析预算跳过；可选分析超限保留并报告，全任务停止则构建失败 |
| B06 | 相同来源内容、不同抓取时间/ETag | generation 和语义产物不变，审计运行报告允许变化 |
| B07 | 新机器只有来源锁、缺少缓存对象 | 错误指明缺少的内容哈希；不暗中联网或拿变化后的上游替代 |
| B08 | 相同锁在不同日期重建、发布新鲜度门禁 | build 语义不受时钟影响；刷新/发布按显式 stale 政策判断 |
| B09 | 输出指向项目根/输入祖先、路径逃逸或占用 | 拒绝覆盖，输入及上次成功包完整 |
| B10 | 未锁定的 check、缺工具的 verify | 局部检查不宣称完整验收；请求完整验证而不能执行时非零 |
| B11 | 引擎代码或运行时依赖变化、无 Git 的安装包 | generation 反映真实实现；移动安装路径不改变指纹，wheel 无 Git 也可构建 |
| C01 | 用户 fork 完整链路 | 达成第 12 节所有门禁 |
| C02 | 含私密设置的生产 base | 不公开发布；隔离合并保留 fake-ip/DNS 与无关设置 |
| C03 | external-config 的 TOML import 和 type binding | 同代三个配置一起加载，类型前缀只组合一次，无静默空导入 |
| C04 | 测试 URL 副本与生产候选 | 地址差异白名单准确，报告绑定候选哈希；改产物后旧验证失效 |
| M01 | domain/ipcidr YAML → MRS | 与可读规范集合及真实内核行为等价；classical 不编 MRS |
| M02 | MRS URL 缺 format 或错误 behavior | 转换/加载门禁失败，不接受默认 yaml |
| M03 | 编译器警告跳项、损坏二进制 | 不因退出码为零或文件非空就接受 |
| M04 | 空分区和编译进程失败 | 不产空 MRS、不截断上一成功产物 |
| M05 | MRS 重复构建和语义 round-trip | 固定工具字节可重建，等价模式文本变化不误判 |
| M06 | 工具缺失/摘要不同/版本不支持 | 正式 build 明确失败或要求新目标验收，不隐式下载/回退 |
| M07 | 重复引用、provider 重命名与覆盖片段 | 每一个真实名称的 format 正确，无用户 provider 碰撞 |
| M08 | 实际 fork 清空预置 format | 桥接不兼容而失败，不声称 MRS 已支持 |
| M09 | 跨 behavior、重复后缀与 Windows 名称碰撞 | 最终全部 provider 到内容/目标唯一，fallback 与平台/并发无关 |
| G01 | 仓库、目录、包、CLI 均为 domainrouter_v2 | 工程元数据、导入、命令及主配置路径使用同一标识；展示名保留 DomainRouter v2 |
| G02 | v1 与 v2 的独立仓库 URL | 发布配置不依赖重定向，新建/迁移远端与本地构建分开执行 |
| G03 | Python 包索引规范名 | 包装归一化与本地导入/CLI 命名不混淆，wheel 可在仓库外安装运行 |
| O01 | 干净克隆运行最小示例 | 无个人文件/密钥/AI 服务，准备工具后能独立完成离线核心演示 |
| O02 | 公开产物、报告和 Python 分发包 | 不含私有 base、缓存原文、URL 凭据、旧虚拟环境或未获许可的数据 |
| O03 | 许可和贡献资料 | 代码与规则数据来源分开，能按 CONTRIBUTING 复现核心测试 |
| H01 | 新电脑只有交接文档的空工作区 | 能从固定远端提交取得迁移资料，不依赖旧绝对路径或虚拟环境 |
| H02 | 超长规范的分册与入口 | 全部章节、原有回归及语义完整；文件可逐份读取，短提示不超过粘贴限制 |
| A01 | 每日 schedule 与 workflow_dispatch | 都进入同一刷新/构建/验证管线；计划每天一次，时区换算正确 |
| A02 | 上游内容改变、304、缓存缺失 | 新内容锁定后生效；304 须有经哈希校验的对象；缓存不代替刷新 |
| A03 | 每日内容未变 | 仍执行构建与必需验证并保留运行记录，不制造空提交或新 generation |
| A04 | 下载/解析/编译/验证失败 | 工作流失败，发布步骤不执行，旧 latest 与所有成功产物完整 |
| A05 | 手动与定时发布并发 | 共享互斥策略，不取消进行中的发布，不发生覆盖/强推或跨代混用 |
| A06 | 发布开关未启用与生产设置未提供 | 仍可交付并测试每日生成；不声称已发布或已接入生产 |

R05 中若混合 classical 明确保留来源顺序，重新排列输入本身会改变参考计划；测试应验证的是并发调度不能改变同一输入的计划，以及纯集合成员重排不改变集合含义，不能强求所有有运行行为的任意排列完全相同。

属性测试至少覆盖域名模式和 IP 集合、随机重复/包含/相邻/边界数据。固定核心测试 profile，每类至少执行 1000 个成功示例，失败例保存为可复现回归数据。随机测试补充证明和边界用例，不能单独证明复杂模式包含。

### 13.4 性能验收

使用合成数据和固定公开小样本，至少测 1 万、10 万项规模；100 万项作为可选压力测试。记录机器、解释器、内核、数据分布、耗时、峰值内存、输出规模、加载时间和稳态匹配分布。

必须包含大面积后缀覆盖、全部互不包含、长标签、多通配、IPv6 大范围、混合 classical 等分布。对相同优化模型，分别测 domain/ipcidr YAML 与 MRS 文件大小、冷加载耗时、加载峰值内存、稳态内存和匹配时延；注明采样/缓存状态。原生 provider 和展开模式分别标记，不混用结果。

先建立基线，再为实际目标机器制定可重复的性能预算。没有测量时不得填写“提升 N 倍”；普通域名和 CIDR 主路径不得依靠全量平方复杂度比较。

## 14. CLI、库接口与诊断

以下是需要实现的命令契约，可以在保持含义的前提下完善参数帮助：

```text
uv run --locked domainrouter_v2 check --config config/domainrouter_v2.toml
uv run --locked domainrouter_v2 check --config config/domainrouter_v2.toml --locked
uv run --locked domainrouter_v2 tools prepare --config config/domainrouter_v2.toml
uv run --locked domainrouter_v2 fetch --config config/domainrouter_v2.toml
uv run --locked domainrouter_v2 fetch --config config/domainrouter_v2.toml --locked
uv run --locked domainrouter_v2 build --config config/domainrouter_v2.toml --locked --out dist
uv run --locked domainrouter_v2 explain --config config/domainrouter_v2.toml --host www.a.hk
uv run --locked domainrouter_v2 explain --config config/domainrouter_v2.toml --ip 192.0.2.42
uv run --locked domainrouter_v2 verify --config config/domainrouter_v2.toml --artifacts dist --level integration
```

- `check`：本地语法、配置和引用检查，不隐式刷新网络。未带 --locked 时，可对未取得的来源记录 pending，语法部分成功须标为 partial；不能因此声称完整规则已通过。带 --locked 时要求解析全部锁定快照，缺失对象退出 3；仍不需要 MRS 编译器，也不等于真实内核验收。
- `tools prepare`：显式按受控工具锁准备当前平台的 MRS 编译器，可联网；不更换版本/锁，不在 build 内隐式调用。转换器/测试内核的准备方式在开发说明中同样显式记录，可使用固定 digest 容器。
- `fetch`：明确联网更新快照和锁文件，先生成完整可接受快照后替换锁文件。`fetch --locked` 只读取现有锁，按原请求获取缺失对象并核对精确哈希；内容变化时报错，不用新内容替换旧锁。已完整且校验通过的对象可复用。允许 stale 的策略只适用于显式刷新/发布，不能让锁定补齐接受错误哈希。
- `build --locked`：纯锁定构建，调用本地固定 MRS 编译器并生成格式桥接配置。build 默认也是锁定方式，--locked 是显式声明；没有隐式刷新模式。缺少内容、base 或工具时报错，不临时联网补齐或改格式。成功产生的是待完整验收的候选包，不自动等于可发布。
- `explain`：报告候选合集、优先命中、目标、来源和优化链；输入元数据不足时返回条件性结果，不能假装完成真实路由判定。
- `verify`：`--level semantic|kernel|integration`，默认 integration。semantic 运行独立语义对照，kernel 还须实际加载/匹配，integration 再经过 fork 与完整受控链路；报告每层状态和候选哈希。缺环境、程序或所需用例时该请求层级不成功且退出非零，不标记完整验收成功。实施阶段可显式只运行已具备的层级，不能把它作为发布门禁。

CLI 调用同一库 API。结构化结果和 JSON 报告应有 schema_version，Web 不解析终端彩色日志来取得结果。CLI 默认不发布、不修改原始规则。以上命令中的 uv 的 --locked 管理 Python 依赖锁；命令后面的 --locked 管理规则来源锁，二者不能混为一个锁。对已安装 wheel，直接运行同名 CLI，应在仓库目录之外仍可用，不能依赖 sys.path 的临时修改。

建议退出码：0 成功；2 输入/配置错误；3 来源/锁定内容错误；4 兼容或行为验证失败；其他非零表示内部错误。warning 默认不失败，CI 可显式启用 warnings-as-errors；error 永远阻止正式产物发布。

最低诊断代码：

| 代码 | 含义 |
| --- | --- |
| E_PARSE_AMBIGUOUS | 无法唯一解释输入 |
| E_RULE_TYPE_UNKNOWN / E_TARGET_UNSUPPORTED | 未知类型 / 目标不支持 |
| E_SOURCE_FETCH / E_SOURCE_FORMAT | 资源获取或格式失败 |
| E_SNAPSHOT_MISSING / E_SNAPSHOT_STALE | 锁内容缺失或超过允许期限 |
| E_ROUTE_REFERENCE / E_ROUTE_FALLBACK | 路由引用错误 / MATCH 结构错误 |
| E_GROUP_REFERENCE / E_GROUP_CYCLE | 策略组引用或循环 |
| E_EMPTY_COLLECTION | 被使用的合集意外为空 |
| E_BACKEND_LOSSY / E_VERIFY_MISMATCH | 输出会损失语义 / 验证结果不一致 |
| E_MRS_COMPILER / E_MRS_CONTENT | 编译工具缺失/失败/摘要不符，或 MRS 与规范模型不一致 |
| E_MRS_BRIDGE / E_PROVIDER_NAME_COLLISION | 未保留 format 或桥接未就绪，provider 名称碰撞 |
| E_OUTPUT_PATH / E_YAML_STRUCTURE | 输出路径不安全或冲突 / YAML 不满足受支持结构 |
| W_SOURCE_POLICY_IGNORED | 原出口按合集目标被剥离 |
| W_OPTIMIZATION_LIMIT | 包含分析达到明确资源限制 |
| I_NORMALIZED / I_DEDUPLICATED / I_COVERED / I_MERGED | 明确的修复或化简事件 |

内部错误不得伪装成无效输入被忽略。日志默认隐藏密钥、认证请求头和敏感查询参数；完整原始内容仅保存在明确允许的本地快照中。
