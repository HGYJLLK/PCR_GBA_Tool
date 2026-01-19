# pcr.py

- 这是一个执行器

```python
def run(self, command):
    """
    所有任务的调度中心

    Args:
        command: 任务名称

    Returns:
        bool: 任务是否成功执行
    """
    try:
        # 执行任务，根据字符串"command"，调用同名的方法
        self.__getattribute__(command)()
        return True # 任务正常结束
    except TaskEnd:
        # 任务正常结束
        return True
        # 捕获游戏运行中的"可恢复"错误
    except GameNotRunningError as e:
        logger.warning(e)
        logger.warning("Game not running, will restart")
        return False # # 返回 False，loop 启动失败
    except (GameStuckError, GameTooManyClickError) as e:
        logger.error(e)
        logger.warning(f"Game stuck, will be restarted in 10 seconds")
        logger.warning("If you are playing by hand, please stop the script")
        self.device.sleep(10)
        return False
    except RequestHumanTakeover:
        logger.critical("Request human takeover")
        exit(1)
    except Exception as e:
        logger.exception(e)
        logger.critical("Unexpected error occurred")
        exit(1)
```

- run 方法它是通用 d 任务执行器，它为调用它的人执行两件事
- 致命错误 (exit(1))：
  - RequestHumanTakeover（需要人来处理）、Exception（未知崩溃）。
  - 这种情况意味着“天塌了”，脚本必须立刻停止，任何重试都没有意义。
- 可恢复错误 (return False)：
  - GameStuckError（游戏卡住）、GameNotRunningError（游戏闪退）。
  - 这种情况意味着“这次任务失败了，但只是个小事故”。
  - run() 方法通过 return False 来告诉“调用它的人”：“任务失败了，但不是世界末日，你可以决定下一步怎么办（比如重启游戏再试一次）。”

## return False 和 exit(1) 区别

- 但是目前只是实现了启动游戏到进入主界面的功能，说白了就是启动游戏，其本质跟重启游戏没有区别
- 那么目前程序上来就是执行 start 这个启动游戏的任务，如果游戏启动失败了，那么根本就没有重启的必要，因此 return False 后和 exit（1）一样了
- 你游戏启动都失败了，哪还有重启再试一次的说法，又不是其他任务

---

- 假设有其他任务，你可以这么理解，你就感受到了重启以及直接结束脚本的区别了

```python
# 这是一个假设的 "run_dailies.py" 文件

from pcr import PCRGBATool
import time

pcr = PCRGBATool()

# 首先，尝试启动游戏 (调用你看到的 run("start"))
logger.info("正在尝试启动游戏...")
start_success = pcr.run("start")

# 如果连启动都失败了，那就不干了
if not start_success:
    logger.error("游戏启动失败，退出所有任务。")
    exit(1)

logger.info("游戏启动成功，开始执行日常任务。")

# 定义今天要做的任务列表
task_list = ["collect_stamina", "arena_fight", "gacha"]

# 这才是你期待的“自动重启”逻辑
for task in task_list:
    logger.info(f"--- 正在执行任务: {task} ---")

    # 尝试执行任务
    success = pcr.run(task)

    # 如果任务失败了 (比如游戏卡住了，run() 返回了 False)
    if not success:
        logger.warning(f"任务 {task} 执行失败！(可恢复错误)")
        logger.info("将尝试重启游戏，并在10秒后重试该任务...")

        pcr.run("restart") # 运行重启任务
        time.sleep(10)

        logger.info(f"--- 正在重试任务: {task} ---")
        success_retry = pcr.run(task) # 重试一次

        if not success_retry:
            logger.error(f"任务 {task} 重试后依然失败，跳过此任务。")

logger.info("所有日常任务已执行完毕。")
```

- 最后说明，pcr.py 目前只是一个启动器，ta 的工作就是启动游戏，启动失败，它就退出

# config 体系

## config.py

- 这是一个配置中心

### bind

#### 运转流程

- 这是整个 config.py 中最难理解的一个函数了
- 为了更好的理解，这里 mock 一个 json 来讲解，假设 json 的格式如下：

```json
{
  "General": {
    "Emulator": {
      "AdbPath": "C:/adb/adb.exe",
      "ScreenshotMethod": "ADB"
    },
    "Debug": {
      "SaveAllScreenshots": false
    }
  },
  "Pcr": {
    "GameSettings": {
      "Language": "JP"
    },
    "Emulator": {
      "ScreenshotMethod": "Uiautomator2"
    }
  }
}
```

1. func 变量变成了字符串 "Pcr"。
2. func_list 经过 insert(0, ...) 操作后，变成了：["General", "Pcr"]。 (它总是先插 "Pcr"，再插 "General"，所以 "General" 永远在最前面)
3. visited = set() (一个空的集合，用来记录处理过的路径)
4. self.bound = {} (一个空的字典，用来创建“地图”)

---

- 最复杂的绑定参数理解

```python
# 绑定参数
visited = set()  # 记录处理过的路径
self.bound.clear()
for func in func_list:
    func_data = self.data.get(func, {})
    for group, group_data in func_data.items():
        if isinstance(group_data, dict):
            for arg, value in group_data.items():
                path = f"{group}.{arg}"
                if path in visited:
                    continue
                arg_name = path_to_arg(path)
                super().__setattr__(arg_name, value)
                self.bound[arg_name] = f"{func}.{path}"
                visited.add(path)
```

- 第一轮循环，访问的是 func = "General"
- 通过 func_data = self.data.get(func, {})获得的 json，即 func_data 应该是这样的

```json
{
  "Emulator": { ... },
  "Debug": { ... }
}
```

- 接下来是 for group, group_data in func_data.items():
- group = "Emulator"，group_data 是 {"AdbPath": "...", "ScreenshotMethod": "..."}
- 接下来是 for arg, value in group_data.items():
- arg = "AdbPath", value = "C:/adb/adb.exe"
- path = f"{group}.{arg}" -> path 变为 "Emulator.AdbPath"
- path 不在 visited 中
- arg_name = path_to_arg(path) -> arg_name 变为 "Emulator_AdbPath"
- `super().__setattr__("Emulator_AdbPath", "C:/adb/adb.exe")`
- 等同于：self.Emulator_AdbPath = "C:/adb/adb.exe"，现在，程序的其他地方就可以用 config.Emulator_AdbPath 来方便地获取这个值了

---

- `self.bound["Emulator_AdbPath"] = "General.Emulator.AdbPath"`
- 这里创建了地图，即"Emulator_AdbPath" 的快捷方式，对应的真实 JSON 路径是 "General.Emulator.AdbPath"
- visited.add("Emulator.AdbPath")
- 其他的是 同理了，后面是讲 func = "Pcr" 的绑定参数

---

```json
{
  "GameSettings": { ... },
  "Emulator": { ... }
}
```

- 这里直接讲相同的地方，即 Emulator
- group = "Emulator"
- group_data 是 {"ScreenshotMethod": "Uiautomator2"}
  - arg = "ScreenshotMethod", value = "Uiautomator2"
  - path 变为 "Emulator.ScreenshotMethod"
  - if path in visited: -> True！ (这个路径在第一轮循环中已经被 General 添加过了)
  - continue -> 这个内内循环被跳过！

#### 图文并茂演示 bind 的 config 和 bound

- bind 同时在两个地方写下了记录：

```bash
[config 对象 (快捷方式)]              [self.bound (地址簿)]
     +--------------------------+          +--------------------------------------+
     |                          |          |                                      |
     | Emulator_Serial = "..."  | <--- 1. 创建快捷方式 | "Emulator_Serial": "Pcr.Emulator.Serial" | <--- 2. 登记地址
     |                          |          |                                      |
     +--------------------------+          +--------------------------------------+
```

- bind 继续添加记录：

```bash
[config 对象 (快捷方式)]              [self.bound (地址簿)]
     +--------------------------+          +--------------------------------------+
     | Emulator_Serial = "..."  |          | "Emulator_Serial": "Pcr.Emulator.Serial" |
     | Emulator_ScreenshotMethod = ... |     | "Emulator_ScreenshotMethod": "..."     |
     | GameSettings_Language = "cn" |          | "GameSettings_Language": "Pcr.Game..."  |
     +--------------------------+          +--------------------------------------+
```

#### bound 的意义

- bound 的意义在于写入，config 的 bound 做了两个工作，读取和写入的时候至关重要
- 读取，采用的是快捷方式，即 config 对象
- 比如 device.py 运行： method = config.Emulator_ScreenshotMethod

```bash
[config 对象 (快捷方式)]              [self.bound (地址簿)]
     +--------------------------+          +--------------------------------------+
     | Emulator_Serial = "..."  |          | ...                                  |
     | Emulator_ScreenshotMethod = ... | ----+     | ...                                  |
     | GameSettings_Language = "cn" |  (只读)     | ...                                  |
     +--------------------------+          +--------------------------------------+
         ^
         |
     [device.py]
```

- 写入是 bound 的唯一使命
- 现在，你的某个代码尝试修改并保存设置： config.GameSettings_Language = "jp"
- `__setattr__` 被触发！

```bash
1. [代码] 尝试修改 "GameSettings_Language"
      |
      v
     [config 对象 (快捷方式)]              [self.bound (地址簿)]
     +--------------------------+          +--------------------------------------+
     | ...                      |          | ...                                  |
     | ...                      |          | ...                                  |
     | GameSettings_Language = "cn" |          | "GameSettings_Language": "Pcr.Game..."  |
     +--------------------------+          +--------------------------------------+
         ^                                     ^
         |                                     |
2. [__setattr__] 拦截到 "GameSettings_Language" 这个 key。
   它会想：“这个 key 对应的 JSON 真实路径是什么？”
                                             |
3. [__setattr__] 立刻去查询 [self.bound (地址簿)]
                                             |
   [__setattr__] 找到了！真实路径是 "Pcr.GameSettings.Language"
                                             |
                                             v
4. [__setattr__] 将修改任务放入 [self.modified (暂存区)]
   self.modified = { "Pcr.GameSettings.Language": "jp" }
      |
      v
5. [__setattr__] 调用 self.save()
      |
      v
6. [save()] 读取 [暂存区]，并使用 deep_set 更新你的 cwj.json 文件。
```

### Function 类

- 这是一个定时调度模块
  - 读取 json 中所有的任务（"Pcr", "PcrDaily"）。
  - 把它们都创建成 Function 对象，放进一个列表：[Function("Pcr"), Function("PcrDaily")]
  - 调度器会遍历这个列表，查看哪个 Function 的 enable 是 true，并且 next_run 的时间已到，然后就去执行它
  - `__str__` 方法是为了方便打印日志，例如 logger.info(f"正在执行任务: {f}")，它会自动打印出 PcrDaily (Enable, 2020-01-01 00:00:00)。

---

- 这是 json 结构

```json
"PcrDaily": {
    "Scheduler": {
      "Enable": true,
      "Command": "PcrDaily",
      "NextRun": "2020-01-01 00:00:00"
    },
    ...
}
```

- Function 类的 data 参数传入的是整个 "PcrDaily" 块！
- 此时 Fucntion(data)的`__init__`就会：
  - self.enable = data["Scheduler"]["Enable"] -> true
  - self.command = data["Scheduler"]["Command"] -> "PcrDaily"
  - self.next_run = data["Scheduler"]["NextRun"] -> "2020-01-01 ..."
- enable: 是否启用
- command: 任务名称（如 "Commission", "Daily", "Main" 等）
- next_run: 下次运行时间

---

- 总结：它的是做什么的呢？
  - 它是用来读取 json 里面的任务，然后创建 Function 对象，然后调度器去执行它。
  - 人话就是：根据 json 里面配置然后执行哪些任务，如果用户启用了某个任务，但是还没到达重置时间就执行过了，那就跳过这个任务
  - alas 并不是直接调用，而是通过 config 对象间接使用，结合一下方法
    - alas.py loop() → alas.py:517-586
    - get_next_task() → alas.py:460-515
    - config.get_next() → config.py:236-261
    - config.get_next_task() → config.py:202-234

## config_updater.py

- pcr.py 是“执行器”，config.py 是“配置中心”，而这个文件是**配置中心的建造者。它是一个开发者工具**，用来自动生成 template.json 和 config_generated.py 文件

```bash
(开发者在项目根目录下运行: python -m module.config.config_updater)
   |
   v
[ConfigGenerator] (工厂)
   |
   +--- 1. 读取 4 个 .yaml 文件
   |      |
   |      +--> [argument.yaml]  (定义了“所有可能的设置”)
   |      +--> [task.yaml]      (定义了“哪些设置属于Pcr”, “哪些属于PcrDaily”)
   |      +--> [default.yaml]   (定义了“默认值”)
   |      +--> [override.yaml]  (定义了“不可修改的锁定值”)
   |
   +--- 2. (工厂开始“制造”...)
   |      |
   |      +--- 3. (制造出 "蓝图")
   |             |
   |             v
   |             [args.json] (一个巨大的 JSON 文件，包含所有任务、所有设置、所有默认值)
   |
   |      +--- 4. (制造出 "Python 默认值")
   |             |
   |             v
   |             [config_generated.py] (一个 .py 文件，PriconneConfig 会继承它)
   |
   v
[ConfigUpdater] (更新器)
   |
   +--- 5. (更新 "空白模板")
   |      |
   |      +--- 读取 [args.json] (蓝图)
   |      +--- 更新 [template.json] (空白模板)
   |
   v
(脚本结束)
```

---

- 那么现在把这三个文件串联起来发生了什么事？

```bash
[你] (在终端输入: python pcr.py)
   |
   v
[pcr.py] (if __name__ == "__main__")
   |
   +--- 1. pcr = PCRGBATool()
   |
   +--- 2. pcr.loop() 被调用
   |
   |
   v
[pcr.py] (loop 函数开始执行...)
   |
   +--- 3. (loop) 第一次访问 self.device
   |      |
   |      |---[调用]---> [pcr.py] (device(self) @cached_property)
   |                       |
   |                       +--- 4. (device) 第一次访问 self.config
   |                              |
   |                              |---[调用]---> [pcr.py] (config(self) @cached_property)
   |                                               |
   |                                               +--- 5. [config.py] PriconneConfig("cwj", task="Pcr")
   |                                                      |
   |                                                      +--- 6. (init_task) self.load()
   |                                                      |      |
   |                                                      |      |---[调用]---> [config_updater.py] (read_file)
   |                                                      |                         |
   |                                                      |                         +--- 7. 加载 "蓝图" [args.json]
   |                                                      |                         +--- 8. 加载你的 [cwj.json]
   |                                                      |                         +--- 9. (config_update) "治疗"
   |                                                      |                         |
   |                                                      |                         <---[返回 完整的"治疗后字典"]
   |                                                      |
   |                                                      +--- 10. (load) self.data = (完整字典)
   |                                                      |
   |                                                      +--- 11. (init_task) self.bind("Pcr")
   |                                                      |      |
   |                                                      |      +--- 12. (bind) 遍历 self.data["Pcr"]
   |                                                      |      +--- 13. (bind) 创建 "Pcr" 的“快捷方式”和“地址簿”
   |                                                      |
   |                                                      <---[返回 config 对象]
   |                                               |
   |                                               <---[返回 config 对象]
   |                              |
   |                              +--- 14. [device.py] Device(config) (初始化...)
   |                              |
   |                              <---[返回 device 对象]
   |                       |
   |                       <---[返回 device 对象]
   |
   +--- 15. (执行流回到了 loop 函数)
   |
   +--- 16. (loop) (继续执行) self.start_log()
   |
   +--- 17. (loop) (继续执行) logger.info("Scheduler: Start task `Start`")
   |
   +--- 18. (loop) (继续执行) success = self.run("start")
   |      |
   |      |---[调用]---> [pcr.py] (run(self, command="start"))
   |                       |
   |                       +--- 19. (run) self.__getattribute__("start")()
   |                              |
   |                              |---[调用]---> [pcr.py] (start(self))
   |                                               |
   |                                               +--- 20. [handler/login.py] LoginHandler(self.config, ...)
   |                                               |
   |                                               +--- 21. (LoginHandler) .app_start()
   |                                               |      |
   |                                               |      +--- (开始用 self.config.Emulator_Serial 等)
   |                                               |      +--- (登录成功...)
   |                                               |
   |                                               <---[返回]
   |                              |
   |                              <---[返回]
   |                       |
   |                       <---[返回 True]
   |
   +--- 22. (执行流回到了 loop 函数)
   |
   +--- 23. (loop) (继续执行) if success: (True)
   |
   +--- 24. (loop) (继续执行) return 0
   |
   v
[pcr.py] (loop 函数执行完毕并返回 0)
   |
   v
[脚本] (程序退出)
```

- config_updater.py 是一个开发者工具，它读取 .yaml 文件来制造 args.json (蓝图) 和 template.json (模板)。
- PriconneConfig 继承了 ConfigUpdater。
- 当你运行 pcr.py 时，PriconneConfig 使用 read_file 方法，将你的 cwj.json 和 args.json (蓝图) 合并，得到一个完整的 self.data。
- bind 方法随后才登场，从这个完整的 self.data 中为当前任务创建“快捷方式”和“地址簿”。

## config_generated.py

- 作用是代码自动补全，它是自动生成的，不用管就是了，你只要把 yaml 编写好就没问题了

```bash
[你的代码编辑器 (IDE)]
+------------------------------------
|
|   def app_start(self):
|
|       # 开发者输入 "config."
|       serial = self.config.
|                           |
|                           +--- [弹出自动补全菜单]
|                                | Emulator_Serial     <--
|                                | Emulator_PackageName  <--
|                                | GameSettings_Language <--
|                                | ...
|
+------------------------------------
```

# device 体系

## device.py

- 这里面有个关键的防卡死机制，它在每个任务里面使用的状况如下：

```bash
[handler/login.py] (LoginHandler)
   |
   +--- 1. "我的目标是登录。我需要'device'来帮我"
   |      handler.device = (传入的 device 对象)
   |
   +--- 2. "开始循环，直到登录成功"
   |
   +--- 3. "先检查一下有没有卡死或循环"
   |      |
   |      |---[调用]---> [device.py] (device.stuck_record_check())
   |      |                 |
   |      |                 <---[返回 False (没卡死)]
   |      |
   |      |---[调用]---> [device.py] (device.click_record_check())
   |      |                 |
   |      |                 <---[返回 False (没循环)]
   |
   +--- 4. "好，现在用'眼睛'截图"
   |      |
   |      |---[调用]---> [device.py] (screen = device.screenshot())
   |                       |
   |                       |  (device 内部调用继承来的)
   |                       |---[调用]---> [module/device/screenshot.py] (Screenshot.screenshot())
   |                                         |
   |                                         +--- (Screenshot 开始用 DroidCast_raw 截图...)
   |                                         |
   |                                         <---[返回 截图]
   |                       |
   |                       <---[返回 截图]
   |
   +--- 5. (LoginHandler 分析截图...)
   |
   +--- 6. "我发现‘登录按钮’在 (100, 200)"
   |
   +--- 7. "现在用'手指'点击"
   |      |
   |      |---[调用]---> [device.py] (device.click(100, 200))
   |                       |
   |                       |  (device 内部调用继承来的)
   |                       |---[调用]---> [module/device/control.py] (Control.click())
   |                                         |
   |                                         +--- (Control 开始用 MaaTouch 点击...)
   |                                         |
   |                                         <---[返回]
   |                       |
   |                       <---[返回]
   |
   +--- 8. "记录一下，我刚点了'登录按钮'"
   |      |
   |      |---[调用]---> [device.py] (device.click_record_add("登录按钮"))
   |
   +--- 9. (回到 步骤 2，开始下一次循环)
```

## adb.py

- 这里和 alas 的不完全一样，因为目前 pcr 只需要支持 mumu 模拟器这个特殊化需求，如果未来需要：
  - 多种模拟器（LDPlayer、Nox、BlueStacks...）
  - HTTP 远程控制
  - 云手机
  - 多设备管理
- 再考虑重构这块为 Alas 的架构

### 分析架构的区别

- AzurLaneAutoScript 架构：

```bash
  Connection (实现 adb_shell, adb_reconnect,adb_start_server, detect_package)
  ↑
  |
  Adb (继承 Connection，添加更多 ADB 功能)
  ↑
  |
  Device
```

- PCR_GBA_Tool 架构：

```bash
  Adb (抽象基类，只定义接口)
  ↑
  |
  Connection (继承 Adb，实现所有方法)
  ↑
  |
  Device
```

- 基于这两个架构得出的不同 d 架构思想
  | 项目 | 设计模式 | 特点 | 适用场景 |
  | :--- | :--- | :--- | :--- |
  | PCR_GBA_Tool | 模板方法模式 | 强制子类实现，灵活性高 | 不同子类需要不同实现 |
  | AzurLaneAutoScript | 继承实现 | 代码复用，统一行为 | 所有子类使用相同逻辑 |

### 总结

- 虽然刚刚提到好像看起来 alas 的性能更优
- 然而并不是，对于 mumu 模拟器的条件下，pcr 更优
- 但是考虑未来的四个因素的情况下，alas 更优
- 也就是说如果 pcr 暂时只需要支持 mumu 设备，那就保持原架构
- 如果有上述四个因素其中之一，就要重构为 alas 架构

## connection

- 这里只对最复杂的逻辑 detect_device 进行讲解
- 这个方法的作用：将 self.serial 转换为一个“确定的、可连接的”设备序列号

**首次扫描 + MuMu12 暴力连接**

```python
def detect_device(self):
    """
    检测并选择设备（找模拟器）
    """
    # ...
    for attempt in range(2):
        devices = self.list_device()
        available = [d for d in devices if d.status == "device"]
        # ...
        if available:
            break # 如果第一次就找到了可用的设备，就跳出循环

            # 如果第一次没找到，并且你是 'auto' 和 Windows
            if (
                self.serial == "auto"
                and platform.system() == "Windows"
                and attempt == 0
            ):
                logger.info("Attempting brute-force ADB connect for MuMu12...")
                # 连接 MuMu12 的默认端口
                for port in [16384, 16385, 16386, 16387, 16388]:
                    try:
                        self.adb_client.connect(f"127.0.0.1:{port}")
                        time.sleep(0.5)
                    except Exception as e:
                        logger.debug(f"Failed to connect 127.0.0.1:{port}: {e}")
                # 再次 list_device，如果已经开启了 mumu12，并且使用了上面的默认接口，应该能找到设备
                continue # 继续进行第二次尝试 (attempt == 1)
```

**预连接 与 最终扫描**

```python
# 如果你指定了 serial (例如 "127.0.0.1:16384")
if ":" in self.serial and not self.serial.startswith("emulator-"):
    try:
        logger.info(f"Attempting to connect to {self.serial}")
        self.adb_client.connect(self.serial) # 主动连接你指定的设备
        time.sleep(1)
    except Exception as e:
        logger.debug(f"Initial connect failed: {e}")

# 获取“最终”的设备列表
devices = self.list_device()
available = [d for d in devices if d.status == "device"]
```

**处理“无设备”情况**

```python
if not available:
    logger.error("No available devices found")
    # 检查配置，看是否允许“重启ADB”作为最后手段
    if self.config.Emulator_AdbRestart:
        logger.info("Attempting to restart ADB server")
        self.adb_start_server() # 重启 ADB
        devices = self.list_device() # 第四次 list_device
        available = [d for d in devices if d.status == "device"]

    if not available:
        # 如果还是没有，就彻底放弃
        logger.critical("No devices available")
        raise EmulatorNotRunningError("No available devices")
```

**最后的 auto 处理**

```python
if self.serial == "auto":
    logger.info("Using AUTO mode to select device")

    # 简单情况：只有一个可用设备
    if len(available) == 1:
        self.serial = available[0].serial # 直接使用它
        logger.info(
            f" Auto selected device: {self.serial} (only one available)"
        )

        # 特殊情况：MuMu 12 识别
    elif len(available) == 2:
        # 处理 MuMu12: 127.0.0.1:7555 和 127.0.0.1:16XXX
        logger.info("Found 2 devices, checking for MuMu12 device pair...")
        # 检查是否有 MuMu12 端口 (16xxx)
        mumu12_devices = [d for d in available if d.is_mumu12_family]
        # 检查是否有 MuMu 端口 (7555)
        has_7555 = any(d.serial == "127.0.0.1:7555" for d in available)

        if mumu12_devices and has_7555:
            # 这是 MuMu 12 的典型特征，忽略 7555
            self.serial = mumu12_devices[0].serial
            logger.info(
                f" Auto selected MuMu12 device: {self.serial} (ignoring 7555)"
            )
        else:
            # 多于 2 个设备,要求手动在 config 文件里指定 serial
            raise RequestHumanTakeover("Please specify device serial in config")
    else:
        logger.error(
            f"Multiple devices found ({len(available)}): {[d.serial for d in available]}"
        )
        raise RequestHumanTakeover("Please specify device serial in config")
```

**指定 serial**

```python
else: # self.serial != "auto"
    # 检查你指定的 serial 是否在“可用”列表中
    if not any(d.serial == self.serial for d in available):
        logger.error(f"Device {self.serial} not found in available devices")
        # 你指定的设备不在那，抛出错误
        raise EmulatorNotRunningError(f"Device {self.serial} not found")
```

**MuMu 12 动态端口追踪**

- auto 或 指定 模式都执行完后，self.serial 已经有了一个确定的值。但 MuMu 12 还有一个特性：它有时会**切换端口**（比如你配置了 16384，但这次它启动在了 16385）
- pcr 会检查你最终选定的 serial（比如 127.0.0.1:16384）
- 如果这个设备是 MuMu 12，它会做最后一次确认
- 如果 16384 不在可用列表里，它不会立刻失败，而是会去**环顾四周**
- 如果它发现 16385（16384 的邻居）在列表里，它会**猜测** MuMu 12 只是换了个端口
- 它会自动将 self.serial 从 127.0.0.1:16384 切换到 127.0.0.1:16385

```python
# ... (MuMu 12 7555 端口重定向, 省略...) ...
current_device = None
for d in available:
    if d.serial == self.serial:
        current_device = d
        break

# 检查你选中的设备是否是 MuMu 12 ...
if current_device and current_device.is_mumu12_family:
    matched = False # ... 检查它是否真的在列表里
    for device in available:
        if device.is_mumu12_family and device.port == current_device.port:
            matched = True
            break

    if not matched:
        # 如果你配置的 16384 不在，但 16385 (在±2范围内) 在...
        for device in available:
            if device.is_mumu12_family:
                port_diff = device.port - current_device.port
                if -2 <= port_diff <= 2:
                    # 自动“修正” self.serial 到新的端口
                    logger.info(
                        f"MuMu12 serial switched {self.serial} -> {device.serial}"
                    )
                    self.serial = device.serial
                    break

logger.info(f"Selected device: {self.serial}")
```

## control.py

### handle_control_check

- 作用：检查控制是否正常

```python
def handle_control_check(self, button):
  """
    Args:
      button: Button对象或操作名称
  """
  # Will be overridden in Device
  pass
```

- 此方法是在 device.py 里面实现的
- 用于记录点击历史、检查异常点击模式以及防止游戏卡死

### multi_click(连点)

- click 和 swipe 是最底层的操作，而它是对这些底层操作的封装
- 使用场景：需要快速、重复地点击同一个位置，通常是为了调整数量或加速
  - 使用扫荡券：当你打活动或者刷装备时，你想刷 50 次，你不可能写一个循环调用 50 次 device.click（那样太慢，而且日志会爆炸）。你调用 multi_click(PLUS_BUTTON, 10) 连续点 10 次加号
  - 剧情快进：虽然有 Skip 按钮，但有些过场动画需要点击屏幕来让它显示下一句对话

### long_click(长按)

- click 和 swipe 是最底层的操作，而它是对这些底层操作的封装
- 使用场景：需要按住不动一段时间
  - 喂经验药水：在角色升级界面，如果你想把角色从 Lv.1 升到 Lv.100，你需要点几百次药水。但是，如果你长按药水图标，游戏会自动快速连续喂药
  - 查看详情：在装备列表或掉落列表，长按装备图标可以弹出一个悬浮窗，显示装备的详细属性和合成路径
  - 技能说明：在战斗界面或角色界面，长按技能图标查看技能描述

# login.py

- 作用：登录的业务逻辑
- login.py 它是一个脚本，**专门负责“启动游戏并登录到主界面”这个单一任务**，它只做业务逻辑，识别这些不是它做的，而是 UI 类那里“继承”来的

# ui.py

- **导航系统/GPS**
- 作用：**“页面导航”**，它继承 ModuleBase（图像识别核心），以及使用 Page (“地图”)，提供**在游戏中任意导航**的能力

# page.py

- 定义游戏中的“地点”

```python
def __init__(self, check_button):
    """
    初始化页面

    Args:
        check_button (Button): 用于识别该页面的特征按钮
    """
    self.check_button = check_button # 用于识别该页面的特征按钮
    self.links = {} # 存放 check_button所在的页面到其他页面的导航链接
    # 自动获取变量名作为页面名称
    (filename, line_number, function_name, text) = traceback.extract_stack()[-2]
    self.name = text[: text.find("=")].strip()
    self.parent = None
    # 注册到全局页面表
    Page.all_pages[self.name] = self
```

- 当开发者在文件底部写 page_main = Page(MAIN_CHECK) 时
- check_button：把 MAIN_CHECK (一个 Button 对象) 保存为这个页面的**地标**
  > UI 类的 appear() 就是靠这个“地标”来识别**我现在是不是在主界面**的
- links：初始化一个空的“出路”字典，存放“从本页面可以去往哪里”
- self.name：自动读取代码，把变量名 "page_main" 字符串赋值给 self.name
- Page.all_pages：它把 self (这个 page_main 实例) 添加到全局的“地图”字典 Page.all_pages 中

---

```python
def link(self, button, destination):
    """
    定义到其他页面的导航链接

    Args:
        button (Button): 点击此按钮可到达目标页面
        destination (Page): 目标页面
    """
    self.links[destination] = button
```

- 当开发者写 page_main.link(button=ADVENTURE, destination=page_adventure) 时
  - “从 page_main（我）出发，如果你点击 ADVENTURE（按钮），你就会到达 page_adventure（目的地）。”
  - self.links 字典就变成了：{page_adventure: ADVENTURE}

---

**GPS 寻路算法**

```python
@classmethod
def init_connection(cls, destination):
    """
    使用 A* 算法初始化页面间的路径（反向BFS）

    Args:
        destination (Page): 目标页面
    """
    cls.clear_connection() # 清空旧的导航路线

    visited = [destination] # 从目的地开始
    visited = set(visited)
    while 1:
        new = visited.copy()
        for page in visited:
            for link in cls.iter_pages(): # 遍历地图上所有节点
                if link in visited:
                    continue
                # 判断"link" 能不能“到达” "page"？
                if page in link.links:
                    # “link”的“下一步” (parent) 就是 "page"
                    link.parent = page
                    new.add(link)
        if len(new) == len(visited):
            break
        visited = new
```

- 假设目标是 page_team_battle (公会战界面)
- init_connection 启动：它从 page_team_battle 开始反向搜索
  - 循环 1：
    - “谁能一步到达 page_team_battle？”
    - 它遍历 all_pages，发现 page_adventure.links 里有 page_team_battle。
    - 它设置：page_adventure.parent = page_team_battle。(意思是：“如果你在 adventure，下一步应该去 team_battle”)
  - 循环 2：
    - “谁能一步到达 page_team_battle 或 page_adventure？”
    - 它发现 page_main.links 里有 page_adventure。
    - 它设置：page_main.parent = page_main。(意思是：“如果你在 main，下一步应该去 adventure”)。
- 完成：寻路结束。parent 属性现在存储了从任何地方到 page_team_battle 的**下一步**。

# scroll.py

- 作用：滚动条读取和控制

# template.py

## 最佳匹配

- 作用：处理**全屏搜索 和 位置完全不固定**的小图标

- match_result (定位并转化为 Button)

```python
def match_result(self, image, name=None):
    """
    返回匹配结果（相似度 + 位置）

    Args:
        image: 全屏截图
        name (str): 按钮名称

    Returns:
        float: 相似度
        Button: 匹配位置的 Button 对象
        """
    res = cv2.matchTemplate(image, self.image, cv2.TM_CCOEFF_NORMED)
    _, sim, _, point = cv2.minMaxLoc(res)
    # print(self.file, sim)

    # 转化为 Button
    #    point 是找到的坐标 (x, y)
    #    _point_to_button 会创建一个新的 Button 对象，
    #    把它的 area 设置在这个 (x, y) 上。
    button = self._point_to_button(point, image=image, name=name)
    return sim, button
```

- 假设你要找屏幕上随机出现的一个“宝箱”
- 你不需要知道宝箱在哪
- 调用 match_result，它会告诉你：“找到了（相似度 0.9）”，并且直接给你一个 Button 对象
- 你可以直接拿着这个“新出炉”的 Button 对象去调用 device.click(button)，实现**指哪打哪**

---

## 匹配分析

### 要求

- 调用方法需要分析需要什么
  - 检查是否存在
  - 获取坐标去点击
- 如果是前者，
  - match()
  - match_luma()
  - match_binary()
- 如果是后者，
  - match_result()
  - match_luma_result()

### 匹配原理

- match 系列（彩色/标准匹配）
  - 原理：使用原图（彩色或加载时的默认格式）进行匹配
  - 适用场景：默认首选。适用于大多数图标、按钮、立绘
  - 对应方法：match()、match_result()
- luma 系列（亮度/灰度匹配）
  - 原理：把大图和模板都转成灰度图 (Grayscale) 再匹配。忽略颜色，只看明暗关系
  - 适用场景：变色图标，比如一个按钮选中时是蓝色，未选中时是灰色，但形状没变。用 luma 可以同时匹配这两种状态
  - 对应方法：match_luma()、match_luma_result()
- binary 系列（二值化匹配）
  - 原理：把大图和模板都变成纯黑白 (0 和 1)，只保留轮廓形状
  - 适用场景
    - 背景非常复杂，颜色干扰极大，但目标的轮廓非常清晰（比如白色的文字、纯色的简单图标）
    - 文字识别辅助或者非常简易的 UI 图标
  - 对应方法：match_binary()

### 应用场景总结

| 想要什么？     | 图片特征             | **使用**              | 备注                            |
| :------------- | :------------------- | :-------------------- | :------------------------------ |
| **点击**       | 正常图标/按钮        | **`match_result()`**  | **最常用！** 返回坐标，直接点击 |
| **点击**       | 按钮颜色会变 (亮/暗) | `match_luma_result()` | 忽略颜色，只认形状              |
| **检查在不在** | 正常图标/按钮        | **`match()`**         | **最常用！** 逻辑判断用         |
| **检查在不在** | 按钮颜色会变         | `match_luma()`        | 忽略颜色                        |
| **检查在不在** | 纯轮廓/复杂背景      | `match_binary()`      | 只看轮廓                        |

## 重复出现

- match_multi (找目标重复出现的位置)

```python
def match_multi(self, image, scaling=1.0, similarity=0.85, threshold=3, name=None):
    """
    匹配目标出现的所有位置（返回所有匹配位置）

    Args:
        image: 全屏截图
        scaling (int, float): 缩放比例
        similarity (float): 相似度阈值 (0-1)
        threshold (int): 聚类距离阈值，距离小于此值的点会被合并
        name (str): 按钮名称

    Returns:
        list[Button]: 所有匹配位置的 Button 列表
    """
    scaling = 1 / scaling
    if scaling != 1.0:
        image = cv2.resize(image, None, fx=scaling, fy=scaling)

    raw = image
    if self.is_gif:
        result = []
        for template in self.image:
            res = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
            # 找到所有相似度 > 0.85 的点
            res = np.array(np.where(res > similarity)).T[:, ::-1].tolist()
            result += res
        result = np.array(result)
    else:
        result = cv2.matchTemplate(image, self.image, cv2.TM_CCOEFF_NORMED)
        result = np.array(np.where(result > similarity)).T[:, ::-1]

    # result: np.array([[x0, y0], [x1, y1], ...)
    if scaling != 1.0:
        result = np.round(result / scaling).astype(int)
    # 把靠得很近的点合并成一个 (Points.group)
    result = Points(result).group(threshold=threshold)
    # 返回一堆 Button 对象
    return [self._point_to_button(point, image=raw, name=name) for point in result]
```

- 这用于处理“列表”或“多个敌人”。
  - 比如屏幕上有 5 个“敌人头像 B”（注意这个头像 B 是相同的）
  - match_multi 会一次性把这 5 个头像的位置都找出来。
  - 它返回一个 Button 列表：[enemy1, enemy2, ...]。
  - 你可以遍历这个列表，一个一个点击。

---

- template.py 结合 button.py 能够实现完整的图像识别功能

```bash
[base/base.py] (ModuleBase)
   |
   +--- 1. appear(button) -> [base/button.py] (定点打击)
   |
   +--- 2. appear(template) -> [base/template.py] (全屏雷达)
            |
            +--- match() -> True/False (有没有敌人？)
            |
            +--- match_result() -> Button (敌人在哪？给我个目标)
            |
            +--- match_multi() -> [Button, Button...] (所有敌人在哪？)
```

# mask.py

- 作用：遮罩过滤器，用于辅助 Template 图像识别
- 典型的应用场景：
  - 排除干扰 (去噪)
    - Q：你想全屏找一个“怪物图标”。但屏幕背景非常花哨，或者 UI 上有很多动态特效（闪烁的光效），这会导致 Template.match 误判或匹配度降低
    - A：做一个 Mask，把可能出现怪物的区域涂白，把背景和特效区域涂黑
    - 效果：Template 在黑色背景上找图标，干扰几乎为零，匹配度极高
  - 限定区域搜索 (类似 Button.area)
    - Q：Template.match 默认是全屏搜索。如果你只想在屏幕左上角找，但又不想每次都裁剪图片（代码麻烦）
    - A：做一个只有左上角是白色的 Mask
    - 效果：mask.apply(screenshot) 后，除了左上角，全屏都黑了。Template 即使全屏搜索，也只能在左上角找到目标
  - 特定颜色提取
    - Mask 通常是预定义的图片，但可以动态生成遮罩（比如“把所有红色的地方变白”），然后 apply 到原图上，只保留红色物体

---

- 结合 Template、Button 之后，可以达到这样的效果

```bash
[感知工具箱]
   |
   +--- [Button] (定点识别)
   |      - 用于 UI 按钮，已知大概位置。
   |
   +--- [Template] (全屏搜索)
   |      - 用于 怪物/掉落物，位置随机。
   |
   +--- [Scroll] (动态感知)
   |      - 用于 列表进度。
   |
   +--- [Mask] (过滤器/遮光罩) <--- 新成员
          - 用于 预处理截图。
          - 配合 Template 使用： Screenshot -> Mask.apply -> Template.match
```

---

## 角色选择应用场景

- 这里假设一个界面，在 pcr 里面使用的本质是一样的

```bash
╔════════════════════════════════════════════════════════════════════╗

║ [返回] [物品] [商店] [设置] [关闭] ║

╠════════════════════════════════════════════════════════════════════╣

║ ║

║ 角色选择与管理 ║

║ ║

╠════════════════════════════════════════════════════════════════════╣

║ ║

║ ╔═════════════════════════════════════════════╗ ▲ ║

║ ║ [角色A - Lv.30] ║ █ ║

║ ║ [角色B - Lv.45] <--- 当前选中 ║ █ ║

║ ║ [角色C - Lv.20] ║ █ (垂直滚动条) ║

║ ║ [角色D - Lv.50] ║ █ ║

║ ║ [角色E - Lv.15] ║ █ ║

║ ║ [角色F - Lv.35] ║ █ ║

║ ║ [角色G - Lv.25] ║ ▼ ║

║ ╚═════════════════════════════════════════════╝ ║

╠════════════════════════════════════════════════════════════════════╣

║ ║

║ ╭───────╮ ╭───────╮ ╭───────╮ ╭───────╮ ╭───────╮ ║

║ │ B │ │ C │ │ A │ │ D │ │ E │ ║

║ │ Lv.45 │ │ Lv.20 │ │ Lv.30 │ │ Lv.50 │ │ Lv.15 │ ║

║ ╰───────╯ ╰───────╯ ╰───────╯ ╰───────╯ ╰───────╯ ║

╚════════════════════════════════════════════════════════════════════╝
```

- pcr 当选择了角色都时候，它会从中间滚动列表栏里面去到底部的队伍栏
- 如果不使用遮罩，全屏搜索的时候 pcr 会认为同一个角色的头像（比如 角色 B）同时出现在了两个地方
- 又或者可能会先找到底部的 B，也可能先找到中间的 B，这会导致逻辑混乱（比如你想把 B 放入队伍，结果脚本点到了已经在队伍里的 B，导致把它下阵了）

### 选择角色

- 目的是“在列表中找到角色 B 并点击它”
- 通过应用 mask，这个遮罩的中间区域是白色（保留），其他区域（顶部菜单、底部队伍）是黑色（遮挡）
- 应用遮罩的效果大致如下：

```bash
████████████████████████████████████████████████████████████████████
████████████████████████████████████████████████████████████████████
████████████████████████████████████████████████████████████████████
██                                                                ██
██  ╔═════════════════════════════════════════════╗  ▲            ██
██  ║ [角色A - Lv.30]                           ║  █            ██
██  ║ [角色B - Lv.45] <--- 目标                  ║  █            ██
██  ║ [角色C - Lv.20]                           ║  █            ██
██  ║ [角色D - Lv.50]                           ║  █            ██
██  ║ [角色E - Lv.15]                           ║  █            ██
██  ║ [角色F - Lv.35]                           ║  █            ██
██  ║ [角色G - Lv.25]                           ║  ▼            ██
██  ╚═════════════════════════════════════════════╝               ██
██                                                                ██
████████████████████████████████████████████████████████████████████
████████████████████████████████████████████████████████████████████
████████████████████████████████████████████████████████████████████
```

- 当你调用 TEMPLATE_CHAR_B.match_result(masked_image) 时
- 底部的“角色 B”已经被涂黑了，计算机根本看不见它
- 计算机只能找到中间列表里的那个 B
- 返回的坐标是绝对准确的列表位置，你可以直接点击

### 验证上阵

- 目的是：“检查角色 B 是否已经上阵了”
- 通过应用 mask，这个遮罩只有底部区域是白色，其他是黑色
- 应用遮罩的效果大致如下：

```bash
████████████████████████████████████████████████████████████████████
████████████████████████████████████████████████████████████████████
████████████████████████████████████████████████████████████████████
████████████████████████████████████████████████████████████████████
████████████████████████████████████████████████████████████████████
████████████████████████████████████████████████████████████████████
████████████████████████████████████████████████████████████████████
████████████████████████████████████████████████████████████████████
████████████████████████████████████████████████████████████████████
██                                                                ██
██   ╭───────╮  ╭───────╮  ╭───────╮  ╭───────╮  ╭───────╮        ██
██   │ B  │  │ C  │  │ A  │  │ D  │  │ E  │        ██
██   │ Lv.45 │  │ Lv.20 │  │ Lv.30 │  │ Lv.50 │  │ Lv.15 │        ██
██   ╰───────╯  ╰───────╯  ╰───────╯  ╰───────╯  ╰───────╯        ██
████████████████████████████████████████████████████████████████████
```

- 当你调用 TEMPLATE_CHAR_B.match(masked_image) 时
- 列表里的 B 已经被涂黑了
- 如果底部有 B，返回 True；如果没有，返回 False
- 这完美实现了**验证**功能，而且绝对不会被列表里的内容干扰

# timer.py

## @timer (调试装饰器)

- 作用：记录函数运行时间

```python
def timer(function):
    """
    Decorator to time a function, for debug only
    """

    @wraps(function)
    def function_timer(*args, **kwargs):
        start = time()
        result = function(*args, **kwargs)
        cost = time() - start
        print(f"{function.__name__}: {cost:.10f} s")
        return result

    return function_timer
```

- 工作原理：在函数运行前记录当前时间，在函数运行后再次记录时间，然后计算两者之差，并打印出这个函数花费了多少秒
- 使用方式：在方法的定义上一行加上 @timer

```python
# 示例：
from module.base.timer import timer

@timer  # <--- 像这样使用
def my_complex_image_recognition():
    # ...
```

## 日期时间

### future_time(string)

- 例子：future_time("05:00") (PCR 的每日重置时间)
- 如果现在是 11 月 17 日 04:00，它返回 11 月 17 日 05:00
- 如果现在是 11 月 17 日 06:00 (已经过了)，它返回 11 月 18 日 05:00

### future_time_range

- 作用：修正 future_time 在处理“进行中的”跨天任务时产生的逻辑 Bug

```python
def future_time_range(string):
    """
    处理跨天的时间范围

    Args:
        string (str): Such as 23:30-06:30.

    Returns:
        tuple(datetime.datetime): (time start, time end).
    """
    start, end = [future_time(s) for s in string.split("-")]
    if start > end:
        start = start - timedelta(days=1)
    return start, end
```

- 假设是现在是周一晚上 8 点（20 点），提供的时间范围是 23:30-06:30
  - future_time 自动给出了正确的范围 (周一 23:30, 周二 06:30)
  - if 语句判断为 False，不执行
  - 脚本拿到了正确的未来范围
- 假设现在是周二凌晨 2 点
  - 由于 future_time 是计算未来并且不具备跨天，它给出了一个“错误”的范围：(周二 23:30, 周二 06:30)
  - 这是一个**反向**的范围，start 比 end 还晚
  - 此时，if start > end: 这行**修复代码**触发
  - 此时脚本知道，程序正在处理一个已经开始的跨天范围，它必须把 start 的日期减去一天
  - start 被修正回了“昨天”（周一 23:30）
  - 脚本拿到了正确的**当前**范围 (周一 23:30, 周二 06:30)

### 应用分析

- 日期时间是任务调度的核心，举例分析即：
  - PcrDaily 处理器在启动时会调用 past_time("05:00") 找到“上一个重置时间”
  - 它会检查 NextRun (来自 config.json) 是否早于“上一个重置时间”
  - 如果是，PcrDaily 处理器就知道：“新的一天来了，我必须执行日常任务！”time_range_active 则用于检查“现在是不是公会战时间？”或“现在是不是双倍掉落活动？”

---

- 假设为项目添加一个新功能：“只在 N 倍掉落活动期间，才去刷困难图 (Hard Quest)”
- 首先定义 config.json

```json
{
    "Pcr": { ... },
    "PcrDaily": { ... },
    "HardQuestEvent": {
        "Scheduler": {
            "Enable": true,
            "NextRun": "2020-01-01 00:00:00",
            "Command": "HardQuestEvent",
            ...
        },
        "Settings": {
            "EventTimeRange": "23:00-07:00"
        }
    }
}
```

- 接着编写你的任务处理文件的代码（handler/hard_quest.py）

```python
from module.ui.ui import UI
from module.ui.page import page_hard_quest
from module.logger import logger
from module.base.timer import future_time_range, time_range_active

class HardQuestHandler(UI):

    def HardQuestEvent(self):
        """
        这就是 pcr.py 的 run(command) 最终会调用的方法
        """
        logger.hr("Hard Quest Event Handler")

        # 从配置中读取“时间字符串”
        time_str = self.config.get_value("HardQuestEvent.Settings.EventTimeRange")
        # time_str 现在是 "23:00-07:00"

        # future_time_range
        event_range = future_time_range(time_str)

        # time_range_active
        if time_range_active(event_range):
            logger.info(f"活动 {time_str} 正在进行中，开始刷 H 图！")

            # 调用“GPS”
            self.ui_ensure(page_hard_quest) # “确保在困难图界面”

            # ... (开始刷图，调用 scroll, button 等)

        else:
            logger.info(f"现在不是 {time_str} 活动时间，跳过 H 图。")

        return True
```

## Timer 类

- 这是一个“间隔计时器”，本质是防抖和节流的底层实现
  - 防抖：规定信号必须稳定一段时间才触发。对应 Timer(limit=1, count=3) 的用法（确认状态）
  - 节流：规定单位时间内只能触发一次。对应 Timer(limit=2) 的用法（冷却时间）
- 作用：“技能冷却”、“稳重观察”

### 技能冷却

- 应用场景：防止疯狂点击同一个按钮（限制频率）
- 示例：比如玩游戏，有一个技能叫“火球术”，它的冷却时间 (CD) 是 2 秒
- 转换代码：Timer(limit=2)
- 工作流：
  - “第一次免费”原则：刚见面 (0 秒)，第一次按技能键，Timer 查看没有记录，即 if self.\_start <= 0: return True，直接使用
  - 0.5 秒后：想再次按技能键，Timer 查看记录，过了 0.5 秒，未达到 2s，return False
  - 2.1 秒后：再次按技能键，Timer 查看记录，过了 2.1 秒，达到 2s，return True

### 防抖

- 应用场景：比如前往主界面，是否真的进入主界面了。防止屏幕刚好卡了一下，显示了 1.5 秒的黑屏。防止脚本跑得太快，可能 0.1 秒内就识别了 5 次，依然可能是一瞬间的画面闪烁
- 示例：比如等人，远处走来一个人影。你是个近视眼（就像图像识别有时候会出错），你不敢确定那是不是你朋友。为了不认错人（防止误操作），你给自己定了个规矩：“我必须盯着他看够 1.5 秒，而且要确认 4 次，我才敢上去打招呼。
- 转换代码：Timer(limit=1.5, count=4)
- 工作流：
  - 第 1 次看 (0.1 秒)，你觉得好像是它，Timer 检查次数不够、时间不够，return False
  - 第 2 次看 (0.5 秒)，你觉得还是像它，Timer 检查次数不够、时间不够，return False
  - ……
  - 第 6 次看 (1.6 秒)，你觉得还是它，Timer 检查次数够了、时间够了，return True

### 初始化

```python
def __init__(self, limit, count=0):
    self.limit = limit  # 点击频率（最快多久能点一次，单位：秒）
    self.count = count  # 次数
    self._start = 0.0   # 0.0 表示"未启动/空闲"，>0 表示"计时中"
    self._access = 0    # 计数器：记录 reached() 被调用的次数
```

### start(self)

- 作用：把状态从“关机”切换到“计时中”

```python
def start(self):
    if self._start <= 0:  # 只有在"关机"状态下才点火
        self._start = time()
        self._access = 0
    return self
```

- 连续调用 10 次 start()，只要第一次启动了，后面 9 次都会被忽略，计时起点不会被重置

### reset(self)

- 作用：不管当前是什么状态，立刻重新开始计时

```python
def reset(self):
    self._start = time() # 强制更新起点为"现在"
    self._access = 0
    return self
```

- 技能冷却转好了，你释放了技能。此时必须调用 reset()，强行开始下一轮 CD 倒计时

### clear(self)

- 作用：彻底停止计时器，把它变回 `__init__` 后的初始状态

```python
def clear(self):
    self._start = 0.0    # 回到"关机"状态
    self._access = self.count # 让计数器直接达标
    return self
```

- 设置 `self._access = self.count` 是基于 reached()里的逻辑
- 假设 count=4，设置`_access`为 count，当它调用 reached 的时候，`_access`会+1，这样结果就是 True
- 因此`_access`是 0 或者 ≥count 的结果都是一样 d

---

- 设置`self._access = self.count`比`self._access = 0`更好
- 假设有一天，开发者修改了 reached 的代码，去掉了那个“快速通道” (else: return True)，把逻辑简化成了这样

```python
def reached(self):
    self._access += 1
    # 如果 start 是 0，time() - 0 很大，时间条件自动满足
    return self._access > self.count and time() - self._start > self.limit
```

- 如果 clear() 里没有写 `self._access = self.count`（而是默认为 0）
- reached 第一次调用时 `_access` 为 1
- 如果 count 是 4。1 > 4 为 False
- clear() 之后的第一次点击失败了！这违背了 clear 的初衷

---

- 如果写了 `self._access = self.count`
- reached 第一次调用时 `_access` 为 5
- 5 > 4 为 True
- 即使去掉了特殊分支，代码依然能正常工作

### reached()

```python
def reached(self):
    self._access += 1  # 只要有人来问，计数器就+1

    # 分支 A: 计时器正在运行 (工作中)
    if self._start > 0:
        # 防抖
        # 必须同时满足：
        # 1. 问的次数够多了 (access > count)
        # 2. 跑的时间够长了 (diff > limit)
        return self._access > self.count and time() - self._start > self.limit

    # 分支 B: 计时器没运行 (关机/新来的)
    else:
        return True
```

- 分支 B：
  - 脚本刚启动，想点击一个按钮。此时不应该有 CD
  - 因为 `_start` 是 0，直接返回 True，脚本立刻点击。点击后，脚本会调用 reset()，`_start` 变成当前时间，计时器进入 分支 A，开始真正的 CD 计算
- 分支 A：
  - 本质“防抖”底层实现
  - 检查是否在主界面 (limit=1.5, count=4)
  - 如果机器巨快，0.1 秒内就识别了 5 次（access=5 > 4），但时间没到（diff < 1.5），return False
  - 如果机器巨卡，卡了 2 秒才识别 1 次（diff > 1.5），但次数不够（access=1 < 4），return False（防止是偶尔一帧的误判）

### reached_and_reset(self)

- 本质“节流”底层实现
- 通常用于 while 循环里的周期性任务

```python
def reached_and_reset(self):
    if self.reached():
        self.reset()
        return True
    else:
        return False
```

- “CD 转好了吗？” (reached)
- “转好了？行，我用了。” (return True)
- “既然用了，立刻重新开始计算 CD。” (reset)

### wait(self)

- 作用：硬阻塞。如果时间没到，我就睡到时间到为止
- 使用要求：必须保证两个操作之间有绝对的间隔，且脚本不需要干别的事

```python
def wait(self):
    diff = self._start + self.limit - time()
    if diff > 0:
        sleep(diff)
```

### from_seconds

- 这是一个面向开发者开发的辅助函数，方便初始化 Timer 对象
- 开发者可能不知道该设置多少 count
- 假设脚本截图一次（加上识别）大概需要 0.5 秒（speed）
- 如果开发者想等待 2 秒 (limit)，那么理论上脚本会截图 2 / 0.5 = 4 次
- 因此通过这个辅助函数，它自动帮你创建了一个 Timer(limit=2, count=4)
- 这里是为了让上层代码只需要关心“时间”，底层的“次数”自动根据机器的大致性能算出来

```python
@classmethod
def from_seconds(cls, limit, speed=0.5):
    count = int(limit / speed)
    return cls(limit, count=count)
```

## 状态验证机制

### 循环验证

#### 核心实现

```python
def combat_preparation(self, balance_hp=False, emotion_reduce=False,
                      auto='combat_auto', fleet_index=1):
    """
    战斗前准备阶段

    核心特点:
    - 手动编写循环逻辑
    - 可以添加任意中间处理器
    - 最终通过 is_combat_executing() 验证进入战斗
    """
    logger.info('Combat preparation.')
    self.device.stuck_record_clear()
    self.device.click_record_clear()
    skip_first_screenshot = True

    # 情绪控制和血量平衡
    if emotion_reduce:
        self.emotion.wait(fleet_index=fleet_index)
    if balance_hp:
        self.hp_balance()

    for _ in self.loop():
        # ==================== 中间处理器 ====================

        # 处理战斗自动化设置
        if self.appear(BATTLE_PREPARATION, offset=(20, 20)):
            if self.handle_combat_automation_set(auto=auto == 'combat_auto'):
                continue

        # 处理退役弹窗
        if self.handle_retirement():
            continue

        # 处理低情绪警告
        if self.handle_combat_low_emotion():
            continue

        # 处理应急维修
        if balance_hp and self.handle_emergency_repair_use():
            continue

        # 点击"准备战斗"按钮
        if self.handle_battle_preparation():
            continue

        # 处理自动化确认弹窗
        if self.handle_combat_automation_confirm():
            continue

        # 处理剧情跳过
        if self.handle_story_skip():
            continue

        # 检测进入加载状态
        if not interval_set:
            if self.is_combat_loading():
                self.device.screenshot_interval_set('combat')
                interval_set = True

        # ==================== 验证：是否进入战斗 ====================
        pause = self.is_combat_executing()
        if pause:
            logger.attr('BattleUI', pause)
            if emotion_reduce:
                self.emotion.reduce(fleet_index)
            break  # 确认进入战斗，退出循环
```

#### 使用场景

- 需要处理多个中间状态（退役、情绪、剧情）
- 需要高度自定义逻辑
- 需要在循环中进行多次判断
  - 检测多个可能的状态
  - 根据不同状态执行不同操作
  - 需要累积某些信息
- 需要精确控制每一步

### ui_click 封装

#### 核心实现

```python
def ui_click(
    self,
    click_button,
    check_button,
    appear_button=None,
    additional=None,
    confirm_wait=1,
    offset=(30, 30),
    retry_wait=10,
    skip_first_screenshot=False,
):
    """
    通用的点击并等待确认方法

    Args:
        click_button (Button): 要点击的按钮
        check_button (Button, callable): 检查按钮或方法
        appear_button (Button, callable): 出现按钮或方法，默认与 click_button 相同
        additional (callable): 额外的处理函数
        confirm_wait (int, float): 确认等待时间
        offset (tuple): 检测偏移量
        retry_wait (int, float): 重试等待时间
        skip_first_screenshot (bool): 是否跳过第一次截图
        """
    logger.hr("UI click")
    if appear_button is None:
        appear_button = click_button

    click_timer = Timer(retry_wait, count=retry_wait // 0.5)
    confirm_wait = confirm_wait if additional is not None else 0
    confirm_timer = Timer(confirm_wait, count=confirm_wait // 0.5).start()

    while 1:
        if skip_first_screenshot:
            skip_first_screenshot = False
        else:
            self.device.screenshot()

        if self.ui_process_check_button(check_button, offset=offset):
            if confirm_timer.reached():
                break
        else:
            confirm_timer.reset()

        # 点击按钮
        if click_timer.reached():
            if (isinstance(appear_button, Button) and self.appear(appear_button, offset=offset)) or (
                callable(appear_button) and appear_button()
            ):
                self.device.click(click_button)
                click_timer.reset()
                continue

        if additional is not None:
            if additional():
                continue
```

#### 使用场景

- 简单的点击 → 验证流程
- 固定的页面跳转
- 只需要标准的弹窗处理

### 对比总结

| 特性         | 循环验证                       | ui_click                      |
| ------------ | ------------------------------ | ----------------------------- |
| **适用场景** | 复杂流程，需要处理多个中间状态 | 简单的点击 → 验证 → 完成流程  |
| **灵活性**   | 高（可自定义所有逻辑）         | 低（依赖 UI 基类）            |
| **可控性**   | 完全控制每一步                 | 封装好的自动处理              |
| **前置依赖** | 无                             | 必须继承 `module.ui.ui.UI` 类 |
| **错误处理** | 手动添加各种 handler           | 内置标准处理流程              |
