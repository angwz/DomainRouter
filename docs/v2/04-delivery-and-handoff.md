# DomainRouter v2 实施规范 · 每日生成、开源交付与实施

版本：1.5 · 日期：2026-11-08 · 第 15～19 节

本分册与入口索引列出的其他三份分册共同构成完整规范，必须顺序阅读；本文件不是单独的需求摘要。

[返回规范入口](../v2-implementation-spec.md)

## 15. 构建、CI、发布与迁移

### 15.1 本地与 CI

- 新实现使用独立包和输出目录，不执行 v1 脚本来得到所谓 v2 产物。
- 依赖锁定，配置和规则模型进行类型检查，执行静态检查与必要格式检查。默认使用 Ruff、mypy、pytest/Hypothesis，版本进入开发依赖锁；不重复引入职责相同的多套格式化工具。
- 常规 CI 离线运行固定快照测试；外部源刷新作为单独、可观察的工作，不让 PR 测试依赖实时公网内容。
- 真实 subconverter/Mihomo 集成任务固定版本和校验摘要，使用测试地址及合成节点，不读取生产订阅。
- MRS 编译工具在显式环境准备步骤获取和校验，正式离线 build 只调用该固定工具。发布任务需要通过 YAML/MRS 行为对照和格式桥接验收。
- 单个完整管线完成刷新/构建/验证/发布，任务依赖明确，不依靠多个并发工作流强推同一分支。
- PR 与验证任务只读权限；发布任务单独获得所需的 contents 写权限。优先使用受限的 GITHUB_TOKEN；不继续要求不必要的 FULL_ACCESS_TOKEN。
- 不在能取得写权限/secret 的 pull_request_target 或 workflow_run 任务中检出并执行未信任 PR 代码。外部 Actions 固定可核验的完整提交 SHA 或已验证的工作流依赖锁；不把移动的 tag 当不可变标识。发布只接受受信任 ref 的本次验证包及对应哈希，不盲信其他任务上传的同名 artifact。
- CI 不以代码格式检查通过替代行为检查，也不把集成任务跳过当成通过。

### 15.2 发布一致性

先在新临时目录构建和验证，成功后更新工作产物。失败不清空上次成功发布，不先删旧文件再尝试构建。

默认保留一次构建完整的版本资源，`rulesets.toml` 中的资源地址固定到对应 generation（构建 ID）目录；稳定入口用于取得最新配置。构建 ID 来自输入与配置等确定性内容，不由包含自身的最终输出哈希递归计算。

同一 generation 一起发布，旧 generation 在声明的保留期内可用。现有稳定路径作为迁移兼容入口时，必须明确它们没有跨多次下载的快照保证。

`groups.toml` 与 `rulesets.toml` 的实际导入接法应绑定同一 generation，或在已验证的整合入口中一同使用。Git 单次提交不等于所有客户端和转换器缓存会同时刷新，必须测试旧/新缓存组合，并保留回滚入口。

MRS 发布单位同时包含两个 TOML、provider 覆盖片段、获准公开的完整 base、各规则资源及清单。生产私有 base 不在公开包中，其 generation 绑定由已验证的部署/导入步骤完成。只发布 MRS 而服务还在使用未预置 format 的旧 base，不算完成迁移。

第 12.3 节的 `external-config.toml` 与该包一起生成；稳定入口只在 generation 完整上传且验证报告匹配后更新。对不可公开的字段使用明确的发布文件 allowlist，而不是递归上传整个 dist/build/cache。不能把 verify 后改动过的配置、规则或 base 再用旧报告发布。

同一 generation 的已发布确定性文件不可覆盖为不同字节；相同内容可跳过上传，哈希冲突则失败。默认只公开确定性产物与 manifest，运行报告保留为 CI artifact 或独立 run 目录，不反复改写不可变 generation 来刷新耗时/时间戳。公开的验证摘要如需纳入版本包，须独立标识且不参与 generation 的自引用计算。

保留期首版默认：最新 10 个成功 generation，以及近 30 天的成功 generation，两者取并集；不自动清理当前生效或显式固定的 generation。调整前须覆盖客户端/转换器缓存与订阅刷新周期，清理只在独立的可审阅流程中执行，不能作为 build 的副作用。

### 15.3 迁移顺序

1. 按第 0.1 节取得固定 v1 只读快照并保存迁移来源；保留旧仓库及其现有发布方式，先在新电脑空工作区完成离线 v2，不改旧远端。
2. 为现有 `my.wei` 和组定义生成 v2 预览、错误/修复/覆盖报告。
3. 处理发现的真实输入歧义；不能按 v1 产物反推并偷偷更改用户语义。
4. 在本地静态服务和隔离转换器上完成验收；已获远端测试发布授权时，可再验证真实托管路径。没有远端仓库不妨碍本地 M4a 验收。
5. 给出 `domainrouter_v2` 的生产入口、MRS 资源、generation base、刷新和回滚方式的具体迁移说明；GitHub 新建及向独立 v2 仓库迁移是单独的远端操作，不在普通 build 中执行。
6. v2 验证通过后再切换主规则工作流，避免 v1/v2 同时更新相同目录；不删除或接管本次范围外的产物。

用户的正式服务、节点和订阅属于环境接入事项；实施者先完成可审阅的本地结果，不因等待生产环境而放弃可独立完成的核心工作。实际对外切换不能被隐藏在普通 build 命令中。

### 15.4 开源项目最低交付

目标是其他人能安装、运行、修改和贡献，而不是只公开当前用户的个人配置。核心不依赖 angwz 的账号、VPS、发布分支或已有私有文件。公开示例和当前用户的迁移配置分开；示例中不能保留真实机场订阅、节点密码、控制器 secret 或 API key。

首次公开发布前必须具备：

- `README.md`：定位、已实现/计划功能、支持的实际版本、Windows/Linux 安装和完整最小演示、语义表入口、MRS 工具准备、配置/发布与故障定位说明。不要把可选 Web/AI 写成已交付能力，也不沿用 v1 中已过时的内核/协议宣传。
- `examples/minimal/`：无联网规则源的 my.wei、合成组、非敏感完整 base、显式空来源锁和配置；用 example.com/保留示例地址，不要求个人节点。执行一次准备步骤后能完成离线 check/build/verify。测试服务器与转换器等集成工具的准备另有固定步骤，不能把首次下载工具称为全程离线。
- `CONTRIBUTING.md`：环境、核心测试命令、类型注册和格式适配约定、添加回归的方式、必需行为门禁；PR 不要求填写生产密钥。`SECURITY.md` 说明缺陷反馈渠道和凭据处理范围，不能承诺无人维护的响应时限。
- `LICENSE`、相应工程许可元数据，以及 `THIRD_PARTY_NOTICES.md` / 数据来源清单：区分新代码、复用的旧代码、Python 依赖、Mihomo/subconverter 测试或编译工具和聚合规则数据。外部二进制的获取与再分发分别处理；调用某工具不等于可以去掉它的许可，聚合数据也不自动变成本项目的同一许可。
- 可安装的 wheel/sdist，安装后不依赖旧仓库或开发工作目录。包内容使用 allowlist；不打包 v1 虚拟环境、个人输入、缓存、测试工具二进制或生产 base。规则发布包与 Python 安装包分别验证、分别版本记录。
- `.gitignore`、`.gitattributes`：排除本地配置/凭据、`.venv`、缓存、构建和工具下载；文本规范与 MRS 二进制区别处理。提交的公共示例不被宽泛忽略规则误排除。至少有一份测试证明公开包不包含敏感 fixture。

当前尚未指定最终代码许可。实施者可以完成来源盘点并提出适合该项目的许可建议，不能擅自给已有第三方内容换许可证。首次开源发布前必须明确选定并放入真实许可文本；仅把仓库设为 public 而没有许可，不算满足本项。该决定不阻塞 M1～M4a 本地开发，需在发布清单明确标记，不用它提前暂停全部实现。

运行数据与程序版本分开管理：代码采用常规版本号和 CHANGELOG；规则 generation 由第 11.5 节内容输入决定。语义/计划版本改变时记录用户可见差异、兼容性与迁移方式。暂不要求遥测、账号系统、插件市场、容器镜像仓库或 PyPI 发布，不为“开源”引入核心不需要的基础设施。

### 15.5 每日自动刷新、生成与发布（核心必需）

每日生成三类规则是已确认需求，不能留作 Web/AI 的可选阶段。默认由 GitHub Actions 执行，新电脑无需每天开机。每个合集仍只生成存在内容的分区：domain MRS、ipcidr MRS、classical YAML；每日重新构建不意味着强制制造三个空文件。

**触发与时间**：使用一个统一工作流（建议 `daily-rules.yml`），必须支持每天一次 schedule 和手动 workflow_dispatch。默认香港时间每天 04:17（Asia/Hong_Kong），采用不声明 timezone 的 UTC cron `17 20 * * *`；若显式使用 timezone，则等价写法是 `17 4 * * *` 配 `Asia/Hong_Kong`，两种选择其一，不能重复配置导致每天两次。小时/分钟是可调整的实施默认值，频率必须为每日。规则/代码变更的 push/PR 另行触发验证，可选择增加成功后立即发布，不代替每天刷新。

GitHub 的 schedule 使用默认分支上的工作流，并可能延迟；公共仓库长期无活动时可能被平台停用。README 应说明如何查看最近运行和重新启用，不把计划时间写成准点 SLA，也不使用空提交掩盖无变化或维持活跃。首次部署时核对默认分支、Actions 启用状态和一次手动完整运行。旧快照当前工作流已改为周更，本次 v2 明确采用每日要求，不能照搬它的 cron。

**每次运行的顺序**：

1. 检出 v2 的受信任输入提交，记录 SHA；使用 v2 自己的 my.wei、组定义和配置，不重新导入 v1。
2. 准备锁定 Python 环境、Mihomo 编译器、隔离 subconverter/内核及固定测试数据；校验版本/摘要。GitHub runner 的临时性不能成为依赖旧电脑缓存的理由。
3. 显式执行普通 fetch 刷新本次全部规则源，再原子接受候选来源锁。缓存可减少传输，HTTP 304 只有在对应对象存在且哈希正确时可复用；不允许只执行 fetch --locked 或 build --locked 就宣称已刷新。默认任一必需来源失败则本次失败；显式 stale 策略按第 6 节，不能偷偷回退。
4. 使用本次接受的锁执行 check --locked、build --locked，生成三类资源、groups/rulesets/base/external-config 与清单；调用同一核心引擎。无来源或无内容变化时也不跳过本次构建和必需验证。
5. 对本次候选执行 integration 验证与发布新鲜度门禁，报告绑定候选哈希；不能因“定时任务”关闭 MRS、no-resolve、路由顺序或真实链路检查。完整测试基线可由独立 CI 建立，候选必须执行与自身内容相关的必需验收。
6. 只有全部必需步骤成功且发布已启用时，才把完整 generation 写到 release 发布位置，并原子更新 latest 入口。公开文件按 allowlist 上传，私有 base/原始快照/凭据不进入公共 artifact 或缓存；最小权限发布 job 使用本仓库受限 GITHUB_TOKEN。
7. 记录本次输入提交、来源变化、generation、验证结果、是否更新发布及最后成功时间。内容未变且该 generation 已完整存在时，验证后跳过重复上传和空提交；运行记录仍显示本日成功生成。不要只因日期变化创建新规则 URL、tag 或 GitHub Release。

定时刷新得到的锁及可分发快照可保留为有明确访问范围和保留期的审计资料；含敏感内容的快照不上传到公开仓库可读的 artifact/cache。不得为保存 fetched_at 每天自动改写 main 或用户输入。历史锁缺对象的恢复遵守第 6 节，缓存只是性能优化，不是永久归档保证。

**发布与失败控制**：定时、手动及其他可写同一 release 的任务共享发布互斥规则，`cancel-in-progress` 为 false，不中断正在提交的发布。只顺序推进已有分支；发现发布基线已变时重新检查，禁止 force push。下载、解析、MRS 编译或验证失败时，job 返回失败并保留上一代；不先清空 release、不发布半套文件、不单独更新 rulesets.toml。默认不自动清理旧 generation，清理仍按第 15.2 节独立执行。

**实施与启用的界线**：M4a 必须写好、检查并本地演练每日管线，交付工作流、配套说明和故障用例；本轮交接不因此授权创建远端或改 VPS。正式部署时以仓库变量 `PUBLISH_ENABLED` 的字符串值 `true` 开启发布；未设置时仅生成/验证候选。M4b 再完成许可、真实公开 base 或私有接入、远端仓库及一次完整手动发布，之后同一管线每天自动发布成功结果。未实际启用前，状态必须写为“每日流程已实现、远端定时/发布未启用”。

## 16. 可选阶段：Web 与 AI

### 16.1 Web

在核心完成后实施，可通过薄 API 调用同一引擎，默认本地或自托管单用户方式。

首要能力为：合集列表、原文编辑、粘贴解析预览、`[Rules]` 拖动排序、策略组编辑、生成物预览、逐项优化原因、域名/IP 命中解释、构建差异和错误定位。

保存必须保留无关原文、注释和单引号语义；预览不自动保存。文件有并发变化时检测版本冲突，不能用旧全文覆盖新文件。原文与结构化表单冲突时，以显式的用户选择和可见差异解决。

界面只呈现会影响用户决策的状态，不要求用户理解内部 trie、哈希桶或测试适配器。匿名公共多人托管、账号系统、协作数据库不属于首版范围。

### 16.2 AI

AI 是可关闭的独立模块，可配置不同服务的 endpoint、model 和凭据引用，不在规则文件、公开仓库或前端构建产物中保存 API key。

输入包括用户明确提供的节点能力、地区/网络情况、规则摘要，以及有来源和时间的资料。模型 API key 不自动赋予联网能力，检索和资料整理需要独立适配。

输出包含：针对具体服务/子域名的建议、依据、资料日期、置信程度、与用户约束的关系和建议差异。服务可用地区等硬约束与速度、流量、延迟偏好分别处理；不能把 HK/US 的个别节点情况当成地区普遍结论。

例如用户可以声明 HK 低延迟但吞吐有限、US 流量充裕但延迟高；AI 在这些个人条件下提出文字交互或视频流量建议。不能只因合集名为 ChinaMedia 就当作全部视频，也不能承诺按域名分流能分开同一主机上的所有文字和视频内容。

AI 不参与确定性去重/合并的必要步骤，不替代形式化包含判断和内核验收。建议先形成可审阅补丁，用户采纳后才成为输入；实施阶段不得默认让 AI 自动改写并发布。

<a id="milestones"></a>

## 17. Claude Code 实施顺序与交付门槛

开始 M1 前做环境与高风险接点核验：先完整读取四份分册和适用工作区指令，按第 0.1 节从远端固定提交读取旧项目资料，确认当前空工作区与实际工具；先用很小的合成 fixture 核验固定 fork 的 TOML type/import、base 字段保留和 MRS 加载。它可以是隔离兼容实验，不必先完成全套解析器。若当前环境无法执行，记录缺项并继续独立核心工作，不能把源码推断写成通过；在进入最终 M3 之前关闭该风险。

### M1：语法、模型与参考行为

交付词法/文档解析、来源格式识别、显式导入过滤、规则类型注册表、统一模型、项目参数策略、诊断和独立参考解释器。先完成第 4 节语义表、P 类测试和基础 D/I/R/N 用例。

通过条件：精确/后缀/通配输入无歧义；第三方上下文不被改变；源位置与诊断可追踪；普通 build 不改写输入。不要在此阶段先建 Web。

### M2：来源、优化与可重建输出

交付下载/快照/锁、domain trie 与通配包含、IP 精确合并、输出规划、可读中间资料、固定 Mihomo 的 MRS 编译、classical YAML/TOML、provider 覆盖片段及 base 合并、清单与解释。

通过条件：所有常规域名/IP 必测化简通过；原生域名成对包含判断精确且无漏候选，不以资源预算跳过；复杂表达式不被损坏；MRS 与可读模型对照通过；数量/参数/分区正确；重复构建和重复优化确定；来源/编译失败不误发布。

### M3：真实链路与性能

交付固定用户 fork 和实际 Mihomo 版本的隔离适配器、未优化/优化及可读/MRS 多路径对照、base-preseed 实际接法、受控 DNS/进程/节点能力测试和格式分开的性能基线。

通过条件：第 12、13 节核心门禁通过，所有输出类型有真实加载与行为证据。未能运行的环境明示，不得将本阶段标记为完成。

### M4a：迁移准备、开源交付与本地发布候选

交付固定 v1 输入快照的 v2 预览及迁移报告、组配置校验、CLI/贡献文档、公共最小示例、Python 安装包、CI 定义和完整本地候选包，补齐正式接入与回滚步骤。必须完成第 15.5 节每日刷新/构建/验证/发布管线的实现与本地演练，并区分未启用的远端状态。不得为凑齐开源包复制未经审阅的个人配置或旧 Git/虚拟环境。

通过条件：保留原文；当前输入逐项有去向或明确未关闭事项，不能声称含未处理 error 的用户 profile 已可发布；公共示例从干净环境完整运行；安装包可在仓库外使用；候选产物与报告属于同一构建；发布/回滚步骤可以复现。缺少当前私有地理库或生产设置时，可完成通用工具交付，但用户 profile 迁移仍单独保持未验证。

### M4b：远端发布和生产启用（独立接入）

创建/接入目标远端仓库、推送及实际发布、连接 VPS 私有 base、真实客户端切换和回滚演练。必须基于具体环境及用户对此类操作的授权执行；本文件给 Claude Code 的默认启动提示仅要求完成 M4a 和准备此阶段，不包含远端写入或 VPS 变更。

通过条件：开源许可就绪；真实发布入口及 generation 绑定通过验证；实际部署版本、缓存、fake-ip/no-resolve 和客户端兼容均有证据；旧入口与回滚可用。没有相关环境访问时不能声称 M4b 已完成，也不能因此不交付已完成的本地核心。

### M5：可选 Web

M1～M4a 稳定后，用户选择启用时再实现第 16.1 节；M4b 的生产启用不必成为 Web 的算法依赖。通过条件为核心命令行仍独立可用、界面与 CLI 结果一致、保存不会丢引号/注释或覆盖并发修改。

### M6：可选 AI

独立实现第 16.2 节。通过条件为可完全关闭、密钥不进入公开产物、建议有来源和差异、采纳前不改变构建结果。

### 核心最终交付检查

- [ ] 可从锁定环境安装，Windows/Linux 基础命令明确。
- [ ] 干净克隆的公共最小示例可运行，wheel 在仓库外可用，程序不依赖个人路径或账号。
- [ ] 所有已确认语义及必测化简有回归覆盖。
- [ ] 每合集不超过三个非空发布资源：domain/ipcidr MRS、classical YAML，rulesets/groups 可用。
- [ ] MRS 工具已固定，可读/MRS 集合与行为等价，二进制不受文本修剪。
- [ ] 实际订阅每个 MRS provider 都有正确 format，重复引用也正确，base 桥接保留原设置。
- [ ] `[Rules]` 的顺序、重复引用和内联位置保真。
- [ ] 去重、包含与合并不扩大、不缩小集合。
- [ ] 默认目标 IP 条件不会因优化新增匹配阶段解析。
- [ ] 原始文件完整，逐项来源和变换原因可查。
- [ ] 用户 fork 与 Mihomo 实际版本完成真实链路对照。
- [ ] 未知/不支持/无法证明的情况有明确结果，没有静默丢弃。
- [ ] 构建可重复，失败不会覆盖上次成功版本。
- [ ] 完整 external-config 绑定同代 groups/rulesets/base，验证报告与候选哈希对应。
- [ ] 性能结论有数据，未执行测试如实标记。
- [ ] GitHub 仓库、本地目录、Python 工程名/包与 CLI 统一为 domainrouter_v2，主配置为 config/domainrouter_v2.toml；其他标识按各自用途命名。
- [ ] Web/AI 不是核心依赖，没有提前扩大到其他模板。
- [ ] 开源资料、代码/数据/工具来源清单齐全，最终 LICENSE 的选定状态明确；未选定不能声称已完成开源发布。
- [ ] M4a 本地交付与 M4b 实际发布/生产启用分别记录状态。
- [ ] 新电脑仅有文档的空工作区可开展实施，旧项目来源提交与选择性迁移可追踪。
- [ ] 每日自动流程已实现：每天刷新来源、生成三类非空资源、验证后统一发布；手动触发可复用同一流程。
- [ ] 无变化不制造空提交，失败不更新 latest；远端定时和发布是否实际启用有明确状态。

实施者交付说明应列出实际变更、验证命令与结果、版本/摘要、性能数据、未完成项目和迁移方式。遇到外部环境差异先给出最小失败用例并完成不受影响的工作，不以“缺少生产密钥”替代隔离测试。

## 18. 证据、参考资料与环境待核验项

### 18.1 已读取的本仓库资料

- `README.md`：v1 定位与 main/release 发布方式。
- `my.wei`：当前合集、混合来源和 `[Rules]`。
- `script/domain_router.py`：当前解析、分类、域名覆盖、CIDR 和输出处理。
- `script/generate_rulesets.py`：当前 TOML 类型、顺序、发布路径和间隔。
- `subconverter_config/groups.toml`：现有策略组源结构与顺序。
- `.github/workflows/`：现有定期构建和多个发布工作流。

这些资料用于迁移与发现问题，不覆盖本规范已确认的 v2 输入语义。v1 的整文件正则解析、通用字符串修剪、跨点通配替换、重复格式化、远端 404 探测输出和多个强推发布任务，不应原样带入 v2。

### 18.2 一手参考

下列链接为设计依据；实现时同时固定实际测试目标，更新相关版本记录。

1. [Mihomo 路由规则及参数](https://wiki.metacubex.one/config/rules/)：规则含义、顺序、no-resolve。
2. [Mihomo 规则集合内容](https://wiki.metacubex.one/config/rule-providers/content/)：三种 behavior 与内容格式。
3. [Mihomo 域名通配语法](https://wiki.metacubex.one/handbook/syntax/)：原生域名模式与字符通配的区别。
4. [用户 fork：provider 生成及参数追加](https://github.com/angwz/subconverter/blob/a33d49e4c6702681a0599add8ecbeedfb5c5a8c0/src/generator/template/templates.cpp#L326)。
5. [用户 fork：展开转换](https://github.com/angwz/subconverter/blob/a33d49e4c6702681a0599add8ecbeedfb5c5a8c0/src/generator/config/ruleconvert.cpp)。
6. [用户 fork：Clash 输出路径选择](https://github.com/angwz/subconverter/blob/a33d49e4c6702681a0599add8ecbeedfb5c5a8c0/src/generator/config/subexport.cpp#L681)。
7. [Mihomo 标签通配验证和 trie](https://github.com/MetaCubeX/mihomo/blob/3f27ef39f8c96bbfbc8b0b9bb10f5c9ef60149d8/component/trie/domain.go)。
8. [domain provider](https://github.com/MetaCubeX/mihomo/blob/3f27ef39f8c96bbfbc8b0b9bb10f5c9ef60149d8/rules/provider/domain_strategy.go)、[ipcidr provider](https://github.com/MetaCubeX/mihomo/blob/3f27ef39f8c96bbfbc8b0b9bb10f5c9ef60149d8/rules/provider/ipcidr_strategy.go)、[classical provider](https://github.com/MetaCubeX/mihomo/blob/3f27ef39f8c96bbfbc8b0b9bb10f5c9ef60149d8/rules/provider/classical_strategy.go)。
9. [RULE-SET 参数处理](https://github.com/MetaCubeX/mihomo/blob/3f27ef39f8c96bbfbc8b0b9bb10f5c9ef60149d8/rules/provider/rule_set.go)、[规则构造和参数](https://github.com/MetaCubeX/mihomo/blob/3f27ef39f8c96bbfbc8b0b9bb10f5c9ef60149d8/rules/parser.go)。
10. [逻辑条件实现](https://github.com/MetaCubeX/mihomo/blob/3f27ef39f8c96bbfbc8b0b9bb10f5c9ef60149d8/rules/logic/logic.go)、[正则引擎](https://github.com/MetaCubeX/mihomo/blob/3f27ef39f8c96bbfbc8b0b9bb10f5c9ef60149d8/rules/common/domain_regex.go)。
11. [fake-ip 元数据与真实匹配流程](https://github.com/MetaCubeX/mihomo/blob/3f27ef39f8c96bbfbc8b0b9bb10f5c9ef60149d8/tunnel/tunnel.go)：解析、进程信息与继续匹配行为。
12. [Python ipaddress](https://docs.python.org/3/library/ipaddress.html#ipaddress.collapse_addresses)：网段与精确折叠工具。
13. [uv 项目与锁](https://docs.astral.sh/uv/concepts/projects/)、[PyYAML](https://pyyaml.org/wiki/PyYAMLDocumentation)、[Hypothesis](https://hypothesis.readthedocs.io/en/latest/)：工程和测试工具参考，具体依赖版本由实施锁定。
14. [Mihomo provider 的 format 与 MRS 转换命令](https://wiki.metacubex.one/config/rule-providers/#format)：mrs 支持 domain/ipcidr，默认格式是 yaml。
15. [MRS 编译器实现](https://github.com/MetaCubeX/mihomo/blob/3f27ef39f8c96bbfbc8b0b9bb10f5c9ef60149d8/rules/provider/mrs_converter.go)、[provider 文本/MRS 解析](https://github.com/MetaCubeX/mihomo/blob/3f27ef39f8c96bbfbc8b0b9bb10f5c9ef60149d8/rules/provider/provider.go)：固定 behavior、reader 和编译失败行为。
16. [GitHub 仓库 API 命名参数](https://docs.github.com/en/rest/repos/repos)、[GitHub 仓库更名](https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository)：大小写与迁移流程。
17. [PEP 8 命名约定](https://peps.python.org/pep-0008/#naming-conventions)：包/模块、类、函数/变量及常量的不同写法；工程标识采用本规范的统一约定。
18. [用户 fork：TOML 规则 binding](https://github.com/angwz/subconverter/blob/a33d49e4c6702681a0599add8ecbeedfb5c5a8c0/src/config/binding.h)、[外部 TOML 入口与 import](https://github.com/angwz/subconverter/blob/a33d49e4c6702681a0599add8ecbeedfb5c5a8c0/src/handler/settings.cpp)：type 如何成为内部前缀，以及同代完整配置的实际结构。
19. [Python 工程名归一化](https://packaging.python.org/en/latest/specifications/name-normalization/)、[uv 安装项目与入口](https://docs.astral.sh/uv/concepts/projects/init/)、[uv 锁定与同步](https://docs.astral.sh/uv/concepts/projects/sync/)：工程命名边界、src 布局、build backend 与 --locked。
20. [IDNA 库与 UTS #46](https://github.com/kjd/idna)：authoring 的显式规范化方法，不代表第三方规则字面量可不加说明地改写。
21. [GitHub Actions 安全使用](https://docs.github.com/en/actions/reference/security/secure-use)、[GitHub 开源许可说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)：开源贡献工作流与真实许可要求。
22. [字面 DOMAIN](https://github.com/MetaCubeX/mihomo/blob/3f27ef39f8c96bbfbc8b0b9bb10f5c9ef60149d8/rules/common/domain.go)、[字面 DOMAIN-SUFFIX](https://github.com/MetaCubeX/mihomo/blob/3f27ef39f8c96bbfbc8b0b9bb10f5c9ef60149d8/rules/common/domain_suffix.go)：不能把显式条件 payload 中的特殊字符直接当原生 provider 模式。
23. [目标 payload 解析与参数](https://github.com/MetaCubeX/mihomo/blob/3f27ef39f8c96bbfbc8b0b9bb10f5c9ef60149d8/rules/common/base.go)、[字符通配实现](https://github.com/MetaCubeX/mihomo/blob/3f27ef39f8c96bbfbc8b0b9bb10f5c9ef60149d8/component/wildcard/wildcard.go)：逗号/空格处理与原生标签模式的语义区别。
24. [v1 固定迁移提交](https://github.com/angwz/DomainRouter/tree/5bcb86f540883712726d37129c5ff493585be6bb)、[旧规则生成工作流](https://github.com/angwz/DomainRouter/blob/5bcb86f540883712726d37129c5ff493585be6bb/.github/workflows/update_domain_rules.yml)：新电脑可从公开仓库读取，v2 的每日要求优先于该快照的周更周期。
25. [GitHub schedule 语义](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)、[Claude Code 的 VS Code 文件引用](https://code.claude.com/docs/en/vs-code#reference-files-and-folders)：每日计划、UTC/时区、默认分支，以及以文件读取替代整份长文粘贴。

### 18.3 不阻塞本地核心实现的待核验项

| 项目 | 当前状态 | 实施时如何关闭 |
| --- | --- | --- |
| VPS 的实际 subconverter 版本与参数 | 已知仓库，未连接 VPS | 取得版本/摘要及脱敏参数，执行相同兼容用例 |
| 用户实际 Mihomo 版本 | 未指定 | 固定可验证目标，并对实际使用版本补充兼容结果 |
| TOML 的生产导入接法和缓存 | 固定提交的 type/import 已核对，第 12.3 节有入口结构；未执行服务 | M3 在隔离转换器复现，M4b 再验证实际托管与缓存 |
| MRS 的 base-preseed 与生产基础配置 | 固定提交字段保留行为已查，未运行转换服务 | M3 用非敏感 fixture 验证；M4b 绑定实际 base 与 generation 后才完成生产接入 |
| MRS 编译工具及客户端兼容矩阵 | 官方方法与源码已核对，未执行编译 | 固定二进制和摘要，完成可读/MRS 多路径对照 |
| GitHub 与本地 v2 名称 | 仓库、目标目录与技术主标识均为 domainrouter_v2，当前 origin 和目录未改 | 后续创建/接入独立 v2 仓库与目标目录，按其更新实际发布配置，保留 v1 回退资料 |
| 性能硬预算 | 尚无测量 | M3 以固定机器和样本建立数据后制定 |
| 最终开源代码许可 | 用户未指定 | 发布前确定并核对代码依赖与数据来源标记 |
| Web 展示风格、AI 服务和检索方式 | 可选阶段尚未实施 | 核心稳定后独立确定，不改变已确认语义 |
| 新电脑迁移来源 | 不存在旧本地目录；v1 公开地址与提交已核实 | 在当前工作区按第 0.1 节获取固定文件并记录哈希 |
| 每日生成与发布 | 需求已确定，当前未写工作流、未创建远端定时 | M4a 实现/本地演练，M4b 启用 Actions 与发布变量并验证 |

以上项目必须如实报告验证状态。它们不授权实施者改写已确认的输入含义，也不要求为了开始 M1 而等待生产环境访问。

### 18.4 历史审查记录（1.0 → 1.1，非当前实施契约）

| 审查发现 | 已采用的修正 |
| --- | --- |
| 发布格式仍全部写 YAML，无法满足 MRS 需求 | 两类 MRS + 一类 YAML；可读资料、编译工具与验证路径独立定义 |
| 旧 fork 不写 format，仅换后缀会按 YAML 读取 MRS | 增加 base-preseed、名称映射、配置保留与失败门禁 |
| 原生通配与字符通配、引号包装容易交叉解释 | 补充上下文与显式类型优先级、层级闭包和反例 |
| 全局相同键去重可能越过求值屏障 | domain/IP 集合去重与 classical 区段去重分开，效果成员保留 |
| 当时的通用模式证明预算与幂等性存在冲突 | 1.1 曾采用固定模式对的状态限制；1.4 已用第 9.3 节精确标签算法替代，原生必需包含不再设该跳过路径 |
| classical 成本层级未列出，参考计划可能被事后重建 | 冻结未优化计划并给出首版纯区段排名/屏障规则 |
| no-resolve 开关与 fork 强制补参冲突，NOT 未知 IP 易误解 | 首版只接受 true，参数作用于叶节点/引用，增加相应回归 |
| 完整配置导入通常带 MATCH，原规范缺少可用过滤契约 | 明确 exclude_types、逐项诊断与允许的提取范围 |
| 锁文件抓取元数据会扰动 generation | 语义快照标识与完整审计锁哈希分开 |
| 相对路径和仓库大小写容易从本地目录错误推导 | 明确 project_root 与小写规范 slug；远端操作不混入构建 |

本次只修正文档，没有执行 MRS 转换、改写 subconverter、重命名 GitHub 仓库或修改 origin。所有新测试场景是实施要求，不是本次已经运行的验证结果。

### 18.5 命名修订（1.2 → 1.3）

用户要求与 paycore 的本地小写习惯对齐，并统一 Python 包、CLI 和配置的项目标识。当前有效约定为：仓库、目录、Python 工程元数据/导入包、CLI 全部使用 `domainrouter_v2`，主配置为 `config/domainrouter_v2.toml`；展示名、类名、常量和协议标识按用途保留大小写。第 1.1 节是命名基线，旧版保留短标识或大写工程目录的约定已被替代。本次仍仅更新文档，未创建远端仓库、修改 origin 或移动本地目录。

### 18.6 完整实施审查（1.3 → 1.4）

| 问题 | 本版修正 |
| --- | --- |
| 原生包含过度依赖通用状态机，超限又削弱必需优化 | 明确长度区间 + 右端 literal 约束的成对充要判断、完备候选索引、闭包合并与固定点；不承诺任意联合最小化 |
| 粘贴块没有结束语法，显式 payload 与正则包装容易误改 | 增加显式/缩进块边界、类型字段词法和不能输出时的失败门禁 |
| 类型支持和 Unicode/IDNA 边界不具体 | 列出首版必需注册项，区分 authoring 规范化与第三方字面语义 |
| MRS 格式桥接缺少可直接实施的整体导入入口 | 核对 fork 的 type/import binding，补 external-config.toml 和同代完整接法 |
| provider 名称在跨 behavior、重复引用与 Windows 下可能碰撞 | 全局规划最终名称，规定确定性 fallback 与碰撞门禁 |
| 检查/构建/验证状态与报告会相互误用 | 明确 partial check、锁定候选构建、验证层级与报告哈希绑定；本地测试无需先发布 |
| 时钟/锁元数据和 manifest 自引用可能破坏重建 | 新鲜度移至 fetch/发布，定义规范输入与 generation，区分确定性清单和运行报告 |
| CLI 被图中误列为可选，安装/工具/包目录不完整 | CLI 必需，补可安装入口、工具锁和显式准备；Python 包输出不占规则 dist |
| 个人可用不等于开源可用，M4 又混入外部部署前提 | 增加公共最小示例、许可/来源/贡献资料和发布权限边界；M4a/M4b 分开 |

本版依然只修改规范与其中的提示语，未实现或运行 v2，没有访问生产服务。新增回归矩阵是后续实现的验收要求；文档静态检查不代表内核测试已通过。

### 18.7 新电脑、文件交接与每日生成（1.4 → 1.5）

已取消旧电脑绝对路径前提，以当前空工作区作为项目根；明确远端固定快照与选择性迁移。规范完整拆为四份分册并由入口索引串联，聊天只发送短启动提示。每日刷新/生成/验证/发布改为核心必需，规定默认时间、同代产物、失败保留、无变化处理与发布启用状态。此修订仍只交付文档包，不编写实现或工作流，不在本机、GitHub 或 VPS 启动定时任务。

## 19. 交给 Claude Code 的启动提示语

把交接包中的 `docs/` 放进新电脑当前打开的 `domainrouter_v2` 根目录，先核对入口索引及四份分册都存在；不需要旧电脑本地目录。只把下面短提示语粘进 Claude Code，或复制 `docs/claude-code-start.md` 的同一内容。完整规范通过文件读取，不合并粘进聊天框。

下面授权下一位实施者编码，不表示本次文档编写已开始实现。仓库读取属于资料获取，实际远端写入和生产启用仍按 M4b 单独处理：

```text
请读取工作区 docs/v2-implementation-spec.md（1.5 入口），再逐份完整读取索引列出的四份分册；被截断时继续分段读取。规范文件不需要粘贴到聊天框。现在开始编码，按 M1→M2→M3→M4a 实施；Web、AI 和 M4b 的实际发布/生产启用暂不执行。

这是新电脑，当前 domainrouter_v2 工作区原本是空目录，没有旧工程。请检查并保留已有文档和工作区指令，在当前项目根创建实现，不使用旧电脑绝对路径。旧资料从 https://github.com/angwz/DomainRouter.git 只读获取，固定提交 5bcb86f540883712726d37129c5ff493585be6bb；按第 0.1 节选择性读取，不运行旧脚本、不复制旧虚拟环境、不更改旧仓库。GitHub 暂不可达时继续独立实现并记录迁移缺项。

严格落实单引号/子域闭包、原生通配的精确包含算法、CIDR 精确合并、[Rules] 顺序、求值屏障和 no-resolve。每合集最多三份非空资源：domain/ipcidr 为 MRS，classical 为 YAML；完成同代 TOML/base/external-config、格式桥接、独立参考与真实 fork/内核验证。

每日自动生成是核心必需：实现 GitHub Actions 的每日刷新来源→锁定构建→验证→成功后统一发布，并支持手动触发。默认香港时间 04:17，失败保留上一版，内容未变不制造空提交；每日流程的实现和演练属于 M4a，真正远端启用属于 M4b。不要每天从旧仓库覆盖 v2 输入。

工程标识统一 domainrouter_v2。交付可安装包、公共最小示例、开源/来源资料、实际测试结果、性能证据与剩余事项；未运行不能当通过。普通实现选择自行处理。当前不创建或推送远端、不实际发布、不改 VPS，最终许可未定列为首次发布前事项，不阻塞独立核心开发。
```
