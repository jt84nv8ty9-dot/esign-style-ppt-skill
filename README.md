# e签宝风格ppt

当前版本 **v2.0.0**，以2026-10-23提供的新版35页模板为准。

## 设计规范

- 封面沿用原画面，只修改文字。
- 内容大标题统一微软雅黑加粗30pt和原深灰至紫色渐变，位置、宽度与对齐可按内容调整。
- 整套使用原稿紫色配色、第2页品牌背景和同一母版。
- 内页可自由设计，不局限于模板里的排版、结构或卡片数量。

## 两种使用方式

1. 根据主题、方向或资料制作新的可编辑PPT。
2. 美化已有PPT草稿，默认保留原意、重要数据、来源、页数和顺序。

调用示例：

> $artifact-template-e 根据我的主题和资料制作8页客户介绍PPT。

> 用e签宝风格ppt美化附件草稿，保留原意、数据和页数，内页按内容重新排版。

## 查看与下载

[技能说明](artifact-template-e/SKILL.md) · [设计规范](artifact-template-e/references/design-system.md) · [内页设计指南](artifact-template-e/references/interior-design.md)

[下载v2.0.0完整技能包](https://github.com/jt84nv8ty9-dot/esign-style-ppt-skill/releases/download/v2.0.0/esign-style-ppt-skill-v2.0.0.zip) · [版本说明](https://github.com/jt84nv8ty9-dot/esign-style-ppt-skill/releases/tag/v2.0.0)

主分支包含完整的50个技能文件，也可通过 Code → Download ZIP 下载。Release中请选上面的完整技能包；自动生成的Source code对应发布时的较早提交。

解压后将整个 artifact-template-e 文件夹放到AI工具的技能目录中。Codex默认目录为用户主目录下的 .codex/skills/。更新时先备份个人修改，再用新版文件夹替换旧安装。显示名称为“e签宝风格ppt”，调用标识保持 artifact-template-e。

## 资源与运行要求

完整包包含新版原始PPT、35页预览、设计规范、两个工作流程、槽位索引与Python辅助脚本。

使用环境须支持加载技能资源及制作可编辑PPT。辅助脚本需要Python 3.9+，负责品牌框架、原页换字与结构检查；内页设计及渲染由PPT制作工具完成。目标电脑需有微软雅黑。只粘贴SKILL.md不能完整复用封面和母版。

本仓库公开。
