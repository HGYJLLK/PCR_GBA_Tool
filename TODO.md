# TODO.md

AI 的任务队列。AI 从上到下执行任务，每完成一个打勾 `[x]`。

**重要规则：**

- ✅ 只能使用 `requirements.txt` 里已有的库
- 🚫 如果必须引入新库，先更新 `requirements.txt` 并在 DEV_LOG.md 中说明理由，等待人类审批
- 📝 每完成一个任务，必须在 DEV_LOG.md 中记录完成情况
- 🔄 如果同一任务重试超过 5 次仍未通过测试，强制停止并请求人类介入
- 🧪 涉及功能修改的任务，必须有对应的测试验证

---

## 🔥 High Priority（高优先级）

<!-- 紧急且重要的任务放这里 -->

### 重构：迁移角色选择模块

- [ ] 修正 `character_selector.py` 的文件位置
  - **原因**：目前 `character_selector.py` 位于 `module/train/`，但它属于通用逻辑，应位于 `module/character/`。
  - **目标**：将文件移动并重命名，同时修复所有引用（如 `tests/test_train.py`）。
  - **涉及文件**：
    - `module/train/character_selector.py` (原文件 -> 删除)
    - `module/character/selector.py` (新文件 -> 移动至此)
    - `tests/test_train.py` (修改引用)
  - **步骤**：
    1. 将 `module/train/character_selector.py` 移动到 `module/character/selector.py`
    2. 搜索全项目，将 `from module.train.character_selector` 改为 `from module.character.selector`
    3. 运行 `tests/test_train.py` 确保重构未破坏原有测试
  - **测试方法**：运行 `python tests/test_train.py`，确保其能正常运行（尽管它还没集成到主程序）。

---

## 🚀 Feature（新功能）

<!-- 新功能开发任务 -->

### 集成训练场自动化 (MVP)

- [ ] 将训练场测试代码重构为正式功能模块
  - **功能描述**：将 `tests/test_ui.py` (导航) 和 `tests/test_battle_train.py` (战斗) 的逻辑合并，封装成主程序可调用的 Handler。
  - **目标**：运行 `python pcr.py` 并传入 `train` 指令时，自动完成：登录 -> 导航至训练场 -> 选择关卡 -> 战斗 -> 结算 -> 返回。
  - **涉及文件**：
    - `module/handler/train.py` (新建：核心逻辑封装)
    - `pcr.py` (修改：注册 train 命令)
    - `module/ui/ui.py`
  - **步骤**：
    1. 创建 `TrainHandler` 类，继承 `UI` 和 `TrainCombat` (多重继承)
    2. 移植 `test_ui.py` 中的导航逻辑，实现 `TrainHandler.navigate_to_train()`
    3. 移植 `test_battle_train.py` 中的战斗逻辑，实现 `TrainHandler.run_combat_loop()`
    4. 在 `pcr.py` 的调度器中注册 `train` 任务
  - **测试方法**：
    - 直接运行 `python pcr.py` (需在 config 中设置 `Command: "train"`)，观察是否完整跑通流程。

### 角色选择器 (Character Selector)

- [ ] 封装通用的角色选择逻辑
  - **功能描述**：将 `tests/test_train.py` 中的自动编队/选人功能提取为通用模块。
  - **目标**：提供一个 `CharacterSelector` 类，供训练场和公会战调用。
  - **来源文件**：`tests/test_train.py`
  - **涉及文件**：
    - `module/character/selector.py` (新建：通用选人逻辑)
    - `module/handler/train.py` (修改：引入 CharacterSelector)
  - **步骤**：
    1. 在 `module/character/` 下创建 `selector.py`
    2. 提取 `select_characters`、`clear_team`、`scroll_and_find` 等通用方法
    3. 确保该模块不依赖具体的 Handler，只依赖 `Device` 和 `Base`
    4. 在 `TrainHandler` 中集成该模块，实现“先选人，后战斗”
  - **测试方法**：
    - 直接运行：`python pcr.py` (Train 模式下观察是否正确选人)

---

## 🐛 Bug Fix（Bug 修复）

<!-- Bug 修复任务 -->

---

## 🔧 Refactor（重构）

<!-- 代码重构任务 -->

---

## 📚 Documentation（文档）

<!-- 文档编写任务 -->

---

## 🧪 Testing（测试）

<!-- 测试相关任务 -->

---

## 🎯 Optimization（优化）

<!-- 性能优化任务 -->

---

## 📦 Dependency（依赖）

<!-- 依赖相关任务 -->

---

## 💡 Research（调研）

<!-- 技术调研任务 -->

---

## ✅ Completed（已完成）

<!-- 已完成的任务移到这里，保留最近 10 个作为参考 -->

### 2025-02-09

- [x] 创建 SKILL.md 文件
  - ✅ 定义了图像识别、设备控制、Handler 开发等标准技能
  - ✅ 添加了常见陷阱和最佳实践
  - 📝 记录在 DEV_LOG.md

---

## 📝 Template（任务模板）

**复制以下模板来创建新任务：**

```markdown
### 任务标题

- [ ] 简短描述（一句话说明要做什么）
  - **问题描述/功能描述**：详细说明
  - **涉及文件**：列出需要修改的文件
  - **步骤**：
    1. 第一步
    2. 第二步
    3. ...
  - **注意事项**：特殊说明
  - **测试方法**：如何验证完成
```

---

## 🤖 AI 使用说明

**AI 的双重职责：执行 + 维护**

本文件是**人与 AI 共同维护**的任务队列：

- 人类负责：添加想法和需求（使用下方模板）
- AI 负责：执行任务 + 审查任务 + 维护任务列表

**AI 工作流程：**

1. **读取任务**：从上到下读取第一个未完成 `[ ]` 的任务

2. **审查任务**：判断任务是否足够明确
   - ✅ **明确任务**（如 "修复 login.py 第 42 行的 IndexError"）→ 直接执行
   - ❌ **模糊任务**（如 "优化性能"、"改进用户体验"）→ **必须先拆解**：
     ```markdown
     ### 优化性能

     - [ ] 测量当前截图方法的性能基线
     - [ ] 对比 DroidCast vs ADB vs NemuIpc 的速度
     - [ ] 识别性能瓶颈（等待人类确认具体优化方向）
     ```
     **然后等待人类确认**，不要自作主张执行

3. **检查依赖**：执行前检查是否缺少配置/依赖
   - 🔴 **缺少关键配置**（如 AWS_ACCESS_KEY、数据库密码）：
     - 在 TODO 顶部的 "🔥 High Priority" 区添加：
       ```markdown
       - [ ] [需人工] 配置环境变量 AWS_ACCESS_KEY
         - **原因**：训练场功能需要访问 S3 存储截图
         - **位置**：.env 文件或系统环境变量
         - **格式**：AWS_ACCESS_KEY=your_key_here
       ```
     - 暂停当前任务，等待人类处理

4. **执行任务**：按照任务描述完成工作
   - 在 DEV_LOG.md 记录实时过程（尝试、失败、调整、成功）
   - 遵循 SKILL.md 中的最佳实践
   - 只使用 requirements.txt 中已有的库

5. **运行测试**：如果有测试方法，必须运行并通过
   - 测试失败 → 分析原因 → 修复 → 重新测试
   - **重试次数限制**：同一任务失败 5 次后，**强制停止**
     - 在 DEV_LOG.md 详细记录 5 次失败的原因
     - 在 TODO 中标记 `[!] [需人工] 任务标题`
     - 请求人类介入

6. **更新状态**：
   - 完成后将 `[ ]` 改为 `[x]`
   - 在 DEV_LOG.md 中记录完成情况（完成时间、关键决策、遇到的问题）
   - 如果是重大变更（新增模块、架构调整），更新 CONTEXT.md
   - Git commit 并 push（使用下方提交信息格式）

7. **继续下一个**：返回步骤 1

**遇到问题：**

- 🔴 **卡住超过 5 次尝试** → 在 DEV_LOG.md 记录所有尝试 → 在 TODO 标记 `[!] [需人工]` → 请求人类介入
- 🟡 **需要新依赖** → 更新 requirements.txt → 在 DEV_LOG.md 说明理由 → 在 TODO 顶部添加 `[需人工] 批准新依赖: xxx` → 等待批准
- 🟢 **需要澄清需求** → 在 DEV_LOG.md 提问 → 在 TODO 标记 `[?] [等待确认]` → 暂停任务等待回复
- 🟠 **发现技术债** → 在 TODO 的 "🔧 Refactor" 区添加重构任务（不要立即执行）

**AI 主动维护 TODO.md 的场景：**

| 场景                 | AI 行动                    | 示例                                 |
| -------------------- | -------------------------- | ------------------------------------ |
| 遇到模糊指令         | 拆解为具体子任务，等待确认 | "优化性能" → 拆解为 3 个具体测量任务 |
| 发现缺少配置         | 在顶部添加高优任务         | 发现没有 API_KEY → 添加配置任务      |
| 任务执行中发现新问题 | 添加 Bug Fix 任务          | 发现登录流程有 Bug → 添加修复任务    |
| 完成任务时发现技术债 | 添加 Refactor 任务         | 代码重复严重 → 添加重构任务          |
| 测试失败超过 5 次    | 标记 `[!] [需人工]`        | 无法解决的错误 → 请求人类介入        |

**提交信息格式：**

```
type: 简短描述

- 详细变更 1
- 详细变更 2

Closes: TODO.md 任务标题
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

其中 type 可以是：`feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`
