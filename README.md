# e签宝风格ppt

根据主题或资料生成可编辑PPT：固定原封面、微软雅黑大标题、紫色配色和品牌背景，内页按内容自由设计。

## v1.1.0：灵活内页布局

- 原稿版式作为参考，不再限制只能选用原页。
- 支持流程、关系图、对照、图文、时间轴、图表和检查矩阵。
- 卡片、固定列数及底部紫色结论带均为可选。
- 新增内页设计指南和整套布局多样性检查，避免反复使用相同构图。
- 共用母版只统一背景与品牌元素，不限定内容区排版。

## 下载与安装

[下载最新版完整技能包](https://github.com/jt84nv8ty9-dot/esign-style-ppt-skill/releases/download/v1.1.0/esign-style-ppt-skill-v1.1.0.zip) · [版本说明](https://github.com/jt84nv8ty9-dot/esign-style-ppt-skill/releases/tag/v1.1.0)

仓库主分支现已包含完整技能文件：[查看 SKILL.md](artifact-template-e/SKILL.md) · [内页设计指南](artifact-template-e/references/interior-design.md)。可通过 Code → Download ZIP 下载主分支，或下载上述发布附件。v1.1.0 发布页自动生成的 Source code 包对应较早提交，安装时请使用完整发布附件或主分支。完整包包含原始18页PPT（含视频）、全部预览、设计规范、灵活内页设计指南、原型目录和Python脚本。

解压后将整个 `artifact-template-e` 文件夹放入：

- macOS：`~/.codex/skills/`
- Windows：`%USERPROFILE%\.codex\skills\`

已有旧版时，用新版文件夹更新原安装；如有个人修改，先备份旧文件夹。

## 使用

在支持技能和本地PPT操作的AI工具中加载完整技能文件夹，然后输入：

> 用e签宝风格ppt，制作一份关于“AI如何提升合同管理效率”的10页PPT。

也可以明确调用：

> $artifact-template-e 根据我的主题制作PPT，保留封面、标题、配色和品牌背景，按内容设计丰富内页。

只发主题也会采用灵活排版，无需逐页指定。显示名称为“e签宝风格ppt”，兼容调用标识仍为 `artifact-template-e`。

## 保持一致的设计元素

- 封面插画、背景、标识和文字框位置保持原样，只替换指定文字。
- 普通内容页大标题为微软雅黑加粗30pt、深灰到紫色渐变。
- 内容页共用原稿“4_空白”布局和同一父母版；内页对象可重新组合。
- 生成后逐页检查文字、图形及整套布局变化；目标电脑需有微软雅黑。

换字与结构检查脚本仅依赖Python 3.9+标准库，适用于原页复用和初始框架。新布局、图表编辑与逐页渲染需要相应PPT制作工具；只粘贴SKILL.md文字不能准确复用封面和母版。

本仓库公开，任何人均可下载完整技能包。
