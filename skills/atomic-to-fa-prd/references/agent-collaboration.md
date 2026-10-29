# FA PRD 专家协作与验收协议

适用范围：PA 调用的纯语音 FA，无 UI。主入口统一组织，七个角色由独立 Agent 执行：能力、研究、产品、交互、测试、评审、产品负责人。角色可以多轮直接交流；正式 PRD 正文、附录和发布快照只由产品负责人（`owner`）写入。交互专家输出独立设计稿，负责人整合。

## 先定验收，再交付

主入口让下游先列出本次需要的字段、证据、阻断条件，登记为 `standards`，再交给上游。项目可增减字段，不得省略能力依据、PA 边界、验证状态和关键规则。`sequence` 是项目内递增事件序号，用来检查标准先于交付；它不是可信时间戳。

建议交接：能力→研究及产品，研究→产品及交互，产品→交互，交互→产品负责人，整合稿→评审团，评审结论→负责人，最终稿→各受影响角色复验。每次交付记录准确输入文件及 SHA256、输出文件、版本、逐条验收结果。退回件不能冒充已验收件。

每位专家分配独立 `agent_id`。四个必需评审视角为 product、technical、algorithm、interaction，分别由不同 Agent 执行；CEO、CFO、COO、operations 根据项目适用性决定并写原因。专家可评审自身草稿，最终一致性审查必须由未写正式稿的独立 Agent 完成。

## 收敛与边界

无需中途等待用户确认需求清单。产品负责人可以调整需求与优先级，登记原因、受影响角色，重做相关交付件和验收。事实、PA 能力基线和已提供原子能力是约束；投票与负责人裁决不能凭空增加能力。缺口放附录。

最多两轮修复复审。仍有正确性或能力边界 blocker/major 时，状态为 blocked，不发布为完成。未执行真实交易、设备或性能测试可作为 validation-gap 保留，写清影响、限制与后续验证；不能以此声称真实业务通过。安全查询实际调用，任何有实际影响的操作需用户明确授权。

最终 review 必须检查能力边界、正文附录、两图与文字、关键规则与用例、指标口径、正确性。结构检查通过后仍需专家阅读语义，检查器不证明产品正确。

## 文件与记录格式

在项目目录保存 `collaboration.json`，路径相对于该文件。每次最终快照统一 `revision`，旧版记录另存，勿混入当前验收。通过下列命令检查：

`python3 <skill>/scripts/check_collaboration.py <project>/collaboration.json`

顶层字段：

| 字段 | 结构与要求 |
| --- | --- |
| schema_version / revision | 新项目 `4`（旧版 `1/2/3` 只作兼容归档）/ 非空字符串 |
| state / repair_rounds | draft、blocked、reviewed、delivered / 整数 0–2 |
| artifacts | `{id,kind,path,sha256,revision,owner}`；正文 kind=body，附录 kind=appendix，owner 必须为 owner；其他如证据、流程源均登记 |
| standards | `{id,producer,consumer,sequence,criteria:[验收项ID]}`；下游给上游的标准 |
| receipts | `{id,standard_id,producer,consumer,agent_id,sequence,revision,inputs:[{artifact_id,sha256}],outputs:[artifact_id],acceptance_artifact_id,status,checks:{验收项ID:pass或fail},limitations:[]}`；agent_id 标识 producer 的实际执行 Agent，消费者验收必须另附带 consumer_agent_id 的验收文件，不能用生产者声明替代；status 为 accepted、accepted-with-limits、returned；带限制必须解释 |
| capability_validation | 同版能力尽调 JSON artifact ID，按 [四阶段验收](capability-gates.md)核对全量清单、文档、示例、业务动作及四回执 |
| reviews | `{id,role,agent_id,revision,inputs:[{artifact_id,sha256}],finding_ids:[]}`；核心四视角必需 |
| optional_reviews | ceo、cfo、coo、operations 各自 `{applicable:布尔值,reason}` |
| findings | `{id,severity,category,status,owner,decision,evidence,limitation}`；severity=blocker/major/minor，status=open/resolved/deferred；仅 validation-gap 可 deferred，且必须有 limitation；关闭需 decision/evidence |
| changes | `{decided_by:owner,reason,affected_roles:[],affected_artifact_ids:[],id,reacceptance_receipt_ids:[]}`；每个受影响角色都有当前版接收验收 |
| final_review | `{agent_id,revision,status:pass,inputs:[{artifact_id,sha256}],checks:{...}}`；覆盖全部最终产物，六项键见上文英文检查项 |
| delivery | `{state,url,readback_inputs:[{artifact_id,sha256}],readback_evidence,diagrams:[]}`；完成交付时 state=verified，两图 kind 分别 user-flow、business-flow，每图有 native_editable=true、node_evidence、preview_evidence |

`reviewed` 与 `delivered` 新版要求七角色都有通过的生产交接记录；测试角色 `test` 必须交付用例、执行状态和缺陷回归记录，阻塞如实保留。所有被引用文件必须存在且实际字节 hash 匹配。`delivered` 额外要求真实 URL、回读记录和两张图的原生节点/预览证据。证据字段指向项目证据文件或真实回读记录，并登记为带 SHA256 的 artifacts；最终独立审查者必须实际打开回读正文、原生节点及预览，不能仅检查路径非空或用一句“通过”替代。记录中的声明可被伪造，检查器只保证文件字节、引用和所记录状态的机械一致性。

## 与既有交接合同兼容

继续使用 `handoff.json`、`interaction.json` 和 `check_handoff.py`，无需修改其 schema。将两份 JSON 作为 artifacts 登记，交互 receipt 引用 handoff 的真实 hash；验收记录附上 check_handoff 输出。既有 `approval` 字段记录用户对自动流程的授权来源及负责人范围决定，不伪造逐需求人工确认。旧合同中逐需求等待用户确认的流程在本协议适用时由本协议替代，授权边界和真实写操作约束继续有效。

默认新建已授权的飞书空间文档，只有用户明确指定才更新已有文档。沿用固定 PRD 目录、简洁正文、研发附录、两张美观简洁的原生可编辑图和已确认指标。发布后回读正文、附录、图节点与预览；本地通过记 reviewed，远端回读通过才记 delivered。


## 当前版实际消费回执（schema 2）

新项目用 schema_version=4；旧版1/2/3须显式用 `--archive` 复查历史结构，不能据此宣称通过新版能力验收。每条 accepted／accepted-with-limits receipt 必须引用 artifacts 中的 acceptance_artifact_id。该文件由实际接受方 Agent 写入，内容为 `{receipt_id,consumer,consumer_agent_id,revision,sequence,inputs:[{artifact_id,sha256}],checks,status,observations,change_ids:[]}`。输入至少覆盖交付 outputs 当前字节；消费者不同于生产者，验收序号晚于交付，逐条观察说明实际看到了什么。验收文件自身也登记哈希，避免循环引用，不将自己列入 inputs。

变更记录提供 id 和 affected_artifact_ids；受影响角色的重验文件必须列 change_ids，绑定本次差量，不能拿旧验收代替。结构脚本能拒绝混版、缺件、旧差量和生产者代填身份；实际是否消费及语义判断仍由独立 Agent 的执行记录和终审核对。

统一用例正本、附录视图、两图源均登记当前 artifact。测试消费者先提出用例与证据要求；产品定预期，能力核动作，交互补事件，评审冻结关键预期。测试表只作为正本投影，不作为第二份规格。

## 测试执行补充

独立测试专家调用 `fa-test-engineering`，按[测试执行与研发验收合同](test-execution.md)提交同版 intake、execution.json 和 acceptance.json；结果回链统一 case ID。缺真实实现时保留阻塞，修复后重跑受影响用例，由负责人和独立评审收敛。正文与远端交付形式不变。

## 能力专家的贯穿验收

能力交接按 [能力尽调与可实现性验收](../../fa-capability-analysis/references/feasibility.md)执行。下游 standards 纳入全量覆盖、参数可获得、组合可衔接、结果可观察、验证状态与能力边界；需求形成、交互完成、测试集形成、PRD 收敛分别记录能力专家实际复验。沿用现有 artifacts、standards、receipts、changes 格式，不新增另一套规格或业务预期。能力或实际返回变化时，负责人登记受影响功能、交互节点、图分支和 case ID，更新对应交付件，再由受影响角色重新验收；关键能力缺失不能用带限制通过掩盖，缩小承诺或移入缺口。

## 信息不丢失的消费检查

每次交接联用 [信息保全合同](information-continuity.md)。continuity.json登记为既有artifact；下游acceptance绑定其哈希并给出逐项处置与原件定位。最终独立评审反查原始约束、能力限制和四路候选，检查索引是否漏登，再查五阶段是否实际落实；blocked不能静默消失。
