# 跨阶段信息保全与消费

目的：原始事实、用户约束、需求、规则、限制、依赖和未解决问题能够传到后续环节；概要只作导航，不能替代原件。复用 collaboration.json 的 artifacts、standards、receipts、changes 及稳定编号，不复制业务预期。

## 每次交接

1. 下游提出标准，上游交准确文件、版本、哈希与内容位置，附本次新增/修改/删除、未决问题和限制。实际读取来源，不能仅阅读上一环节摘要。
2. 下游逐项处置：carried（落实到当前产物）、reference（明确引用附录/来源）、not-applicable（说明理由）、blocked（缺失或矛盾，交回责任方）。关键依据、禁止动作和影响用户结果的限制必须 carried；未决问题不得在摘要中消失。
3. 主持维护 continuity.json 作为既有内容的索引。每项 id 沿用功能/规则/证据编号；若一个功能有多个独立限制或依赖，则分别登记稳定子编号及来源位置。每项覆盖 product、interaction、flows、cases、final 五阶段。flows 要分别定位两图，独立信息查询不强加下单步骤。
4. 项目明确暂缓的事项记录范围决定，保持原件，不生成新设计。发现的候选合并/舍弃保留理由与继承编号；进入基线的内容必须逐项追踪。完整性由独立评审反查用户约束、四路发现和原件，不能靠索引自证。
5. 原件变化使旧哈希失效；按功能→规则/依赖→交互→两图→用例→PRD追查影响，在既有 changes/receipts 中重验。无变化产物可沿用字节，但绑定当前快照和复验结论。外部字段与FA派生规则保留完整输入输出。

## 最小索引

`continuity.json`：continuity_version=2，revision，standard_artifact_id（下游预先制定的已登记标准），state（draft|reviewed），artifacts（复用当前项目登记的 `{id,path,sha256,revision}`），items：
`{id,source_artifact_id,source_locator,required_stages:[],stages:{product|interaction|flows|cases|final:{disposition,artifact_ids:[],locator,reason}}}`。
标准文件含 `continuity_requirements:[{id,required_stages:[]}]`，复用既有 standards 的同版文件，不另建业务规则正本。检查器将条目与必要阶段和该标准逐项对账，拒绝整项删除或必要阶段缩小。标准本身是否覆盖原始资料，由独立下游验收；不能由生产者自行改标准绕过。

每项五阶段都有处置；required_stages由下游预先确定，不能为空；应交条目及必要阶段须在既有 standards 中冻结，独立消费者逐项对照，禁止生产者通过删除整项或缩小必要阶段取得通过。必要阶段只能carried；reference必须指向可读取的同版原件。not-applicable说明业务原因。flows的carried包含 user-flow/business-flow 两个定位。定位应精确到稳定ID、节点、图边、用例或文档段落，不能只写“见附件”。

## 原始需求基线与处置

在既有下游标准文件中增加 `raw_requirements:[{id,source_artifact_id,source_locator}]`。产品负责人从用户要求、项目补充和开发者资料中提取可独立决定的要求，保留原始资料及精确位置；同一来源的不同限制分别编号。独立下游逐条反查原件后冻结标准，并在既有 acceptance 中记录完整性判断。此清单只索引原件，不复制业务预期，也不另建正本。新增或改动须走既有 changes 和受影响角色重新验收。

`continuity.json` 增加 `requirement_decisions:[{id,decision,owner,reason,evidence_artifact_id,evidence_locator,item_ids:[],successor_ids:[]}]`，与冻结 raw_requirements 的编号完整对账。每项都有负责角色、理由及指向已登记决策/交付件的证据位置：

- `adopted`：item_ids 非空，指向现有 items 的功能、规则或限制；successor_ids 为空，沿五阶段落实。
- `merged`／`replaced`：successor_ids 非空，指向基线中承接它的原始需求编号，item_ids 为空；继承不得成环，所有分支最终到 adopted。由独立消费者判断承接内容是否完整，检查器只验证引用链。
- `deferred`／`not-applicable`：两类目标均为空，证据说明暂缓范围或不适用原因，保留原始要求。项目明确暂缓的认证与个人信息按此处理，不生成新设计或用例；后续启用须变更并重验。

执行 `python3 scripts/check_continuity.py continuity.json --require-baseline`；统一最终验收必须启用该参数。旧版无基线格式仅供历史复查，不用于新项目验收。reviewed禁止blocked；draft可记录blocked；必要阶段blocked仍检查失败，报告未闭环。检查器验证引用、哈希、阶段、冻结条目的决定和显式遗漏；原始资料是否枚举完整、定位语义及继承内容是否正确，由独立消费者实际读取后判断。最终review反查用户要求与原始资料，不以索引自证完整。信息保全失败先修复，不以新增文本数量代替覆盖。
