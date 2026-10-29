# 参考与采用边界

整理日期：2026-10-28。本规范是针对当前需求的原创组合，外部材料作为设计方法参考，未整段复制上游 Skill。链接资料会更新，采用前复核当前内容。Star 是仓库热度，不用于证明本规范质量。

| 来源 | 本包借鉴 | 本包另行补充/边界 |
|---|---|---|
| [Google 样例对话设计](https://developers.google.com/assistant/conversation-design/write-sample-dialogs) | 角色扮演、样例对话、实际TTS试听与流程迭代 | 旧 Assistant 方法资料；采用方法，不采用旧平台接入方案 |
| [Alexa Situational Design](https://developer.amazon.com/en-US/alexa/alexa-skills-kit/situational-design) | 语音优先、从真实情境出发 | 业务流程和全双工细则由本包独立定义 |
| [conversational-ux](https://github.com/Owl-Listener/designer-skills/blob/main/interaction-design/skills/conversational-ux/SKILL.md) | 确认、修复、口语表达及多模态检查维度 | 不照搬固定时长/选项数量作为强制阈值 |
| [voice-conversation-design](https://github.com/RobStrayer/voice-agent-skills/blob/main/plugins/voice-foundations/skills/voice-conversation-design/SKILL.md) | 区分停播/取消、结果状态、已播内容与后续对话 | 运行机制须依实际产品验证，社区验证较少 |
| [LiveKit 场景编写](https://github.com/livekit/agent-skills/blob/main/skills/writing-livekit-scenarios/SKILL.md) | 用户目标、成功条件、初始与最终状态、回归集 | 本包不绑定SDK；文本走查与真实音频验证分开 |

本包资料层级：设备、入口及PA/FA能力由使用者提供项目基线；具体接口、性能和业务能力仍待核对。样例对话为设计示例；验证记录只记录实际完成的文本走查和结构校验。

## 项目专属基线

公开包不包含内部架构文档、个人助手需求或历史回读凭证。使用者须提供当前项目架构、PA能力基线及需求来源；示例中的能力、设备和状态契约均须重新核实。附带方向覆盖仅作为设计参考，不能自动变成项目范围。

## 2026-10-29补充调研

本次新增轮次恢复、沟通适应、主动通知、状态与权限、承接上下文及验收口径，详见[语音体验补充规则](voice-experience-extensions.md)。保持conversational-ux原有章节为主体。来源适用边界与采用内容见该文件末尾；补充条款为设计要求，设备与服务表现仍待实测。

## 2026-10-29一致性与工程证据补充

参考用户提供的《v1_语音交互设计评估与Codex参考.md》，选择吸收G2、G1/G6、G4及G3方法，落点为consistency-and-metrics.md和voice-runtime-evidence.md。报告为二手工作参考；未核查的外部延迟值、标准章号与小样本结论未引入阈值。多轮计时规则由本机导航生成稿中实际出现的补问耗时遗漏驱动修订。新业务验证记录位于交付工作区，按实际执行层级报告。
