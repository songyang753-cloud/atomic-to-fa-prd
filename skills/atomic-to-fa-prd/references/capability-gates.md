# 能力尽调与四阶段验收

复用 collaboration.json 的 artifacts、standards、receipts；当前项目用 schema_version=4。旧版可复查，但不代表通过本版能力验收。正文模板不变，以下材料进入附录。项目明确暂缓的需求保留原状，不扩展其规范和用例。

## 阅读与验证顺序

能力专家先枚举用户提供的全部工具、命令、端点和开发者文档导航，精读相关正文、示例、鉴权前提、输入输出、状态及错误说明；记录版本、来源、已读/不可访问及影响。再按产品、交互、测试的具体疑点补查。官方示例逐项转成用户任务机会，记录采用、合并或舍弃理由。仅工具列表不能代替完整文档阅读；文档缺失必须如实登记。

对本期每项业务动作核对参数来源、上下文、返回用途、修改后的失效范围、结果凭据和失败恢复。安全查询实际调用；历史回执和定义分析分别标注，不能替代本轮实测。无授权的有影响操作只分析执行条件，不执行。PA 未明确的能力标待核实。完整链路缺必要能力时缩小承诺或移入能力缺口。

## 结构化记录

collaboration.json 的 capability_validation 指向一个已登记、同版且校验哈希的 JSON artifact，其内容如下。引用一律使用 artifact ID，证据文件须脱敏。

- revision：与项目相同。
- inventory_source_artifact_id：在产品设计前保存的规范化原始清单 JSON artifact，含 capability_ids 和 raw_evidence_artifact_ids；能力 ID 全量对账，原始证据供独立专家核对。
- discovery_artifact_id：同版需求发现 JSON artifact，沿用 capabilities/candidates 正本；所有 include 功能及其能力必须有动作路径。
- documents：列表；每项 id、source、version、status（read/unavailable）、evidence_artifact_id；unavailable 还需 impact。包括完整目录及不可访问项，不以删项制造全覆盖。
- examples：列表；每项 id、document_id、task、capability_ids、decision（adopt/merge/reject）、reason。确实无官方示例时为空，并填写 examples_absence_reason。
- inventory：列表；每项 id、source_artifact_id、required_inputs（字段名列表）、verification（current-query/historical/definition-only/pending/failed）、limitations。逐项与提供的原始发现清单及文档对账；不得仅列已采用能力。
- paths：列表；每项 feature_id、action、capability_id、bindings（必填输入名→来源说明）、result_use、evidence_artifact_ids。覆盖本期每个 external 外部业务动作；组合中的 FA derive 加工与 pa 步骤以 discovery_version=2 的 steps 为正本，不伪造专用端点。四阶段回执须同时消费该正本，核实派生输入字段、计算规则、范围和 PA 依据。跨步参数来源须可追查，PA 依赖须指向已确认基线或明确的降级方案。
- gates：四项，name 为 requirements/interaction/cases/final；receipt_id 指向实际能力专家消费的验收回执；target_artifact_ids 列出当前阶段实际交付件并包含于该回执 outputs。相应 producer 为 product/interaction/test/owner，consumer 为 capability。每个回执 inputs 必须含本能力报告、上述原始清单和需求发现 artifact。报告只引用回执ID，不引用其哈希，避免循环。验收 standard 在交付前制定，独立 consumer 文件实际绑定本阶段产物及当前能力台账哈希。criteria 至少包含 capability-coverage、inputs-results、evidence-boundaries。四次交付及其独立接收验收依次发生，前次接受后才允许后次交付，任何受影响材料修改后重新验收。

四阶段分别检查：需求的逐动作可实现性；交互追问、确认、修改与恢复的真实依据；用例动作、禁止动作及预期结果；最终正文、附录、两图及用例的同版承诺。每次需记录具体观察及未通过项，不能只写 pass。

## 验收边界

check_capability.py 检查引用、必填参数覆盖、已知能力和四阶段回执。能力专家独立对照原始清单确认枚举完整性，逐步核验绑定含义、结果语义和状态变化；机器检查不能证明这些业务事实。缺文档、无运行入口、无设备回执分别保留验证缺口，设计审查和真实业务执行分别报告。

历史记录显式使用 `check_collaboration.py <file> --archive`；默认入口拒绝 schema 1/2/3，避免降级绕过新门禁。
