# 2.1 Config 配置项

module/config/argument/args.json 配置项部分参数说明：

- Emulator（设备控制）

  1. Serial: 设备连接
  2. PackageName: 包含公主连结的包名
  3. Screenshot/ControlMethod: 截图和控制方式

- EmulatorInfo（模拟器信息）

  1. 支持的模拟器
  2. 模拟器路径配置

- Error（错误处理）

  1. HandleError: 错误处理
  2. SaveError: 保存错误截图
  3. ScreenshotLength: 截图保存数量

- Optimization (性能优化)

  1. ScreenshotInterval: 截图间隔
  2. CombatScreenshotInterval: 战斗截图间隔
  3. WhenTaskQueueEmpty: 任务完成后

- Schedule (调度器)

  1. Enable: 启用调度
  2. Command: 执行命令
  3. ServerUpdate: 服务器更新时间

- 整个配置的逻辑走向如下：

1. 在 module/config/argument/\*.yaml 中配置默认参数
   - argument.yaml:定义配置项的结构、类型、默认值等
   - task.yaml: 定义任务相关配置
   - override.yaml: 定义覆盖默认参数的配置项
   - gui.yaml: 定义 GUI 相关配置
2. 这些 yaml 文件将被处理然后在同级目录下生成 args.json 文件
3. 接着从 args.json 中读取参数，然后生成 module/config/config_generator.py（它会包含所有配置项作为类属性）
4. 接着在 config/\*.json 中配置用户自定义参数
5. 最后通过 module/config/config.py 继承 GeneratedConfig 类，读取用户配置文件

## utils

- 这是配置生成器的工具模块，主要定义了代码生成器的规则，以及一些辅助函数

1. read_file：读取 json yaml 文件
2. write_file：写入 json yaml 文件
3. filepath_argument：获取文件路径参数
4. path_to_arg：将路径转换为参数，例: 'Scheduler.Enable' -> 'Scheduler_Enable'
5. parse_value：解析参数值，将字符串转换为数字、布尔值等

## deep

- 处理配置生成器中的深度嵌套的数据

## config_updater

- 处理配置更新器，主要用于更新配置项
- 它是最重要的文件，通过它来实现配置的热更新，即在运行时更新配置项，而无需重启程序
- 它通过读取 argument.yaml 配置文件，获取所有配置项的默认值，然后在运行时将用户自定义的配置项合并到默认值中，生成新的配置项，并写入 args.json 文件，最后生成 config_generator.py 文件

## watcher

- 监听器，用于监听用户自定义配置文件的变化

1. start_watching：启动监听器，开始监听用户的配置文件
2. get_mtime：获取文件修改时间
3. should_reload：判断是否需要重新加载配置文件

## module/config/ - 配置系统定义（开发者层）

- argument.yaml - 参数定义（开发者维护）
- task.yaml - 任务定义
- override.yaml - 强制覆盖
- default.yaml - 默认值覆盖，覆盖 argument.yaml 中的默认值
- 作用: 定义哪些参数存在，参数类型，可选值等

### argument.yaml

- 就是一些基础的通用配置，设备相关、游戏相关、脚本项相关的配置

### task.yaml

- 具体游戏任务的配置

### override.yaml

- **作用**: 强制某些参数的值、类型或显示状态（不可被用户修改）

### default.yaml

**使用场景**:

- 不同任务需要不同默认值
- 某些任务默认启用/禁用
- 预设特定任务的推荐配置

**优先级**:

```
argument.yaml (基础默认值)
    ↓ 被覆盖
default.yaml (任务特定默认值)
    ↓ 被覆盖
用户配置 (config/*.json)
```

## ./config/ - 配置实例（用户层）

- template.json - 配置模板（自动生成）
- pcr1.json, pcr2.json - 用户实际配置
- 作用: 存储用户的实际配置值

### 文件间的关系

```bash
1. argument.yaml        ← 基础定义（最低优先级）
   ↓ 合并
2. default.yaml         ← 任务默认值
   ↓ 合并
3. override.yaml        ← 强制覆盖（最高优先级）
   ↓ 结合
4. task.yaml            ← 定义任务结构
   ↓ 生成
5. args.json            ← 中间合并结果
   ↓ 生成
6. template.json        ← 用户配置模板
```

### 生成流程

```bash
开发者编辑:
    module/config/argument/argument.yaml
    module/config/argument/task.yaml
    module/config/argument/override.yaml
    module/config/argument/default.yaml
    module/config/argument/gui.yaml
        ↓
运行代码生成器:
    python -m module.config.config_updater
        ↓
生成中间文件:
    module/config/argument/args.json (合并所有定义)
        ↓
生成目标文件:
    1. module/config/config_generated.py (Python代码)
    2. config/template.json (配置模板) ← 这就是根目录的 config!
    3. module/config/argument/menu.json (GUI菜单)
        ↓
用户使用:
    1. 复制 template.json → pcr1.json
    2. 修改 pcr1.json 中的配置值
    3. 程序运行时加载 pcr1.json 作为配置
```

## 开发者层开发详解

- 大部分参数都是在 argument.yaml 中进行定义
- 极少数任务，具有特殊性的，才会在 default.yaml 中进行定义

### 定义 argument.yaml（通用定义）

```yaml
# module/config/argument/argument.yaml

# ==================== 通用配置组 ====================

Scheduler:
  Enable:
    type: checkbox
    value: false # ← 通用默认值：大部分任务默认禁用
    option: [true, false]
  NextRun: 2020-01-01 00:00:00
  SuccessInterval:
    value: 0
    valuetype: int
  FailureInterval:
    value: 120
    valuetype: int

BattleConfig:
  AutoBattle:
    type: checkbox
    value: false # ← 通用默认值：大部分任务手动战斗
    option: [true, false]
  BattleSpeed:
    value: x2
    option: [x1, x2, x4]
  UseSkill:
    value: true
    option: [true, false]

StageConfig:
  StageFilter:
    type: textarea
    value: |-
      A1 > A2 > A3       # ← 通用默认值：A 系列关卡
  RunCount:
    value: 100
    valuetype: int
```

---

### 定义 default.yaml（例外配置）

```yaml
# module/config/argument/default.yaml

# ==================== 例外任务的差异化默认值 ====================

Daily:
  Scheduler:
    Enable: true # ← 覆盖：Daily 任务默认启用（与 argument.yaml 不同）
    SuccessInterval: 30 # ← 覆盖：Daily 任务成功后 30 分钟再运行

AutoFarm:
  Scheduler:
    Enable: true # ← 覆盖：自动刷图默认启用
  BattleConfig:
    AutoBattle: true # ← 覆盖：自动刷图默认自动战斗（与 argument.yaml 不同）
    BattleSpeed: x4 # ← 覆盖：自动刷图默认 4 倍速

EventA:
  StageConfig:
    StageFilter: |- # ← 覆盖：A 活动打 A 系列（保持 argument.yaml 的默认值）
      A1 > A2 > A3

EventB:
  StageConfig:
    StageFilter: |- # ← 覆盖：B 活动打 B 系列（不同于 argument.yaml）
      B1 > B2 > B3
```

### 定义 override.yaml（强制覆盖）

- 对于一些不能给用户修改的一些配置，则定义在这里
- 目前项目暂时不需要定义这个
- 后续开发的时候可能会用到

### 定义 task.yaml （任务定义）

- 这个也是一个极其重要的一个文件
- args.json 就是根据 task.yaml 生成的
- 它定义了任务的结构，以及每个任务的配置项
- 如果 task.yaml 没有定义到某个配置项，则尽管 argument.yaml 中有默认值，但不会生成到 args.json 中
