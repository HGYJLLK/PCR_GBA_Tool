---
name: pcr-gba-automation
description: Python automation framework for Princess Connect! Re:Dive Guild Battle. Includes image recognition, device control, handler development, and testing patterns.
---

# PCR GBA Automation Skills

**本文件的性质**: 项目的"工具箱" - 封装标准操作流程和最佳实践

## 📚 使用规范

**何时使用本文件**:
- ✅ 开始新任务前，查找相关技能（如 "如何创建 Handler"）
- ✅ 遇到不确定的操作时，查找最佳实践（如 "Button 检测流程"）
- ✅ 需要避免常见错误时，查看 antipatterns（如 "不要跳过截图"）

**何时更新本文件**:
- ✅ 发现新的通用模式（如 "如何处理多页滚动列表"）
- ✅ 发现新的常见错误（如 "忘记 skip_first_screenshot 导致卡死"）
- ✅ 引入新的技术栈（如 "如何使用新的 OCR 库"）
- ❌ **不要记录**一次性的业务逻辑（如 "训练场第3关的特殊处理"）

**更新格式**:
```markdown
## How to [操作名称]

**[SKILL] 简短描述**

[详细说明，包括参数、返回值、使用场景]

Example:
    [代码示例]

Common mistakes:
    [常见错误示例]
```

**SKILL 标签的含义**:
- 带 `[SKILL]` 标签的函数/方法，表示这是**已验证的标准操作**
- AI 看到 `[SKILL]` 标签，应优先使用这些方法，而不是"重新发明轮子"
- 人类维护者应确保所有 `[SKILL]` 标记的代码都经过审查和测试

---

## When to use this skill

Use this skill when working on PCR_GBA_Tool, specifically when you need to:
- Add new automation features for the game
- Create button definitions for image recognition
- Develop new Handler modules for game logic
- Control Android devices via ADB
- Write tests for automation features
- Navigate the codebase architecture
- Handle exceptions and errors properly
- Follow git workflow and dependency management

## How to create button definitions

**[SKILL] Create a new Button definition using the automated tool**

Always use `dev_tools/create_button.py` instead of manual Photoshop editing:

```bash
# Step 1: Run the tool
python dev_tools/create_button.py

# Step 2: In the browser that opens:
#   - Select the screenshot showing the button
#   - Drag to select button regions
#   - Enter button name and details
#   - Script auto-generates Button definition and saves asset

# Result: Clean Button definition with asset saved to assets/
```

**Benefits:**
- Automatic asset extraction and saving
- Consistent Button definition format
- No manual Photoshop work required

**DON'T do this:**
```python
# ❌ Manually create Button definitions
BUTTON = Button(area=(100, 200, 300, 400), color=(255, 255, 255), ...)
```

## How to check if buttons appear

**[SKILL] Safely check if a button appears on screen**

```python
# Pattern for checking button appearance with proper screenshot
def check_button_safely(self, button: Button, offset=None, similarity=None, interval=0) -> bool:
    """
    [SKILL] Check if button appears with proper screenshot and error handling.

    Args:
        button: Button object to check
        offset: If set, uses template matching instead of color matching
        similarity: Template matching threshold (0.0-1.0)
        interval: Minimum seconds between True returns (prevents rapid clicking)

    Returns:
        True if button appears (and interval elapsed), False otherwise

    Important:
        - MUST call self.device.screenshot() before this
        - Use interval parameter to prevent click loops (GameTooManyClickError)
        - Color matching (default) is faster than template matching (offset set)
    """
    # Example usage in a Handler:
    self.device.screenshot()  # Always screenshot first!
    if self.appear(BUTTON, interval=1.0):  # Only returns True once per second
        self.device.click(BUTTON)
```

**Common mistakes to avoid:**
```python
# ❌ WRONG: No screenshot before detection
if self.appear(BUTTON):
    self.device.click(BUTTON)

# ✅ CORRECT: Always screenshot first
self.device.screenshot()
if self.appear(BUTTON):
    self.device.click(BUTTON)
```

## How to wait for buttons to appear

**[SKILL] Wait for a button to appear with timeout**

```python
def wait_for_button(self, button: Button, timeout=10, skip_first_screenshot=False) -> bool:
    """
    [SKILL] Wait for button to appear with proper timeout handling.

    Args:
        button: Button to wait for
        timeout: Maximum seconds to wait
        skip_first_screenshot: If True, uses existing screenshot

    Returns:
        True if button appeared within timeout, False otherwise

    Example:
        # Wait for login screen to appear
        if self.wait_until_appear(LOGIN_BUTTON, timeout=20):
            logger.info("Login screen loaded")
            self.device.click(LOGIN_BUTTON)
        else:
            raise GameNotRunningError("Login screen did not appear")
    """
    pass
```

## How to take screenshots and detect buttons

**[SKILL] Standard pattern for screenshot + detection**

```python
def standard_detection_flow(self):
    """
    [SKILL] The correct flow for all image recognition operations.

    Pattern:
        1. Take screenshot
        2. Check for buttons/conditions
        3. Perform actions
        4. Repeat

    This is THE fundamental pattern of the entire automation framework.
    """
    # ✅ CORRECT: Proper pattern
    while True:
        self.device.screenshot()  # Step 1: Capture current screen

        if self.appear(BUTTON_A):  # Step 2: Check conditions
            self.device.click(BUTTON_A)  # Step 3: Act
            continue

        if self.appear(BUTTON_B):
            self.device.click(BUTTON_B)
            break

    # ❌ WRONG: Missing screenshot
    if self.appear(BUTTON):  # Will use old/no screenshot data
        self.device.click(BUTTON)
```

## How to click with confirmation

**[SKILL] Click with confirmation check**

```python
def click_with_confirmation(self, click_button: Button, check_button: Button,
                           appear_button=None, retry_wait=2, skip_first_screenshot=False):
    """
    [SKILL] Click a button and wait for confirmation that action succeeded.

    Args:
        click_button: Button to click
        check_button: Button that should appear after successful click
        appear_button: Optional button that must appear before clicking
        retry_wait: Seconds between retries
        skip_first_screenshot: If True, uses existing screenshot

    Returns:
        True if confirmation appeared, False otherwise

    Example:
        # Click "Start Battle" and wait for battle screen
        self.ui_click(
            click_button=START_BATTLE_BUTTON,
            check_button=IN_BATTLE_INDICATOR,
            retry_wait=3
        )

    Use case:
        - Navigating between UI screens
        - Confirming dialog actions
        - Ensuring state transitions completed
    """
    pass
```

## How to create a new Handler module

**[SKILL] Create a new Handler module following project architecture**

**Architecture layers (bottom to top):**
```
Config Layer
    ↓
Device Layer (ADB connection, screenshots, control)
    ↓
Base Layer (ModuleBase, Button, Template, Timer)
    ↓
UI Layer (page navigation, scrolling)
    ↓
Handler Layer (business logic: login, combat, etc.)
    ↓
Scheduler Layer (pcr.py - task orchestration)
```

**Steps to create a new Handler:**

1. **Understand the layer hierarchy:**
   - Config → Device → Base → UI → Handler → Scheduler

2. **Create handler file in module/handler/:**
   - Inherit from UI class (never from ModuleBase directly)
   - UI provides navigation methods (ui_goto, ui_ensure)
   - Name pattern: {Feature}Handler (e.g., LoginHandler, BattleHandler)

3. **Define buttons in assets/{feature}/:**
   - Use create_button.py to generate Button definitions
   - Import buttons at top of handler file
   - Group related buttons together

4. **Implement handler methods:**
   - One method per logical task
   - Use self.device.screenshot() before detection
   - Use self.appear() / self.wait_until_appear() for detection
   - Use proper exception handling (see exception.py)
   - Add interval checks to prevent rapid clicking

5. **Register in scheduler (pcr.py):**
   - Add task name to VALID_TASKS
   - Implement task_handler() method
   - Import handler lazily using @cached_property

**Example Handler:**

```python
from module.ui.ui import UI
from module.handler.assets import *  # Import button definitions

class ExampleHandler(UI):
    def handle_example_task(self):
        """
        Handle the example task flow.

        Raises:
            GameStuckError: If stuck in unexpected state
            RequestHumanTakeover: If manual intervention needed
        """
        logger.hr("Example Task", level=2)

        # Navigate to required page
        self.ui_ensure(page=MAIN_PAGE)

        # Main loop with timeout protection
        timeout = Timer(120).start()
        while True:
            self.device.screenshot()

            # Handle different states
            if self.appear_then_click(EXAMPLE_BUTTON, interval=2):
                timeout.reset()
                continue

            if self.appear(COMPLETE_INDICATOR):
                logger.info("Task completed")
                break

            if timeout.reached():
                raise GameStuckError("Example task timeout")
```

**Common antipatterns to avoid:**

```python
# ❌ WRONG: Handler inheriting from ModuleBase
from module.base.base import ModuleBase

class MyHandler(ModuleBase):  # Missing UI navigation capabilities!
    pass

# ✅ CORRECT: Handler inheriting from UI
from module.ui.ui import UI

class MyHandler(UI):  # Has navigation, detection, and all base capabilities
    pass
```

```python
# ❌ WRONG: Violating layer hierarchy
# Scheduler directly accessing Device methods
class PCRGBATool:
    def run(self, command):
        self.device.screenshot()  # Scheduler shouldn't do this
        self.device.click(BUTTON)  # This is Handler's job

# ✅ CORRECT: Respect layer boundaries
# Scheduler → Handler → UI → Base → Device
class PCRGBATool:
    def run(self, command):
        handler = self.get_handler(command)  # Get appropriate handler
        handler.run()  # Handler manages device interaction
```

## How to handle exceptions

**[SKILL] Proper exception handling following project hierarchy**

**Exception Types (module/exception.py):**

1. **Recoverable Errors** (caught in pcr.py, task retried):
   - `GameStuckError`: Game is stuck, restart task
   - `GameNotRunningError`: Game not running, restart app
   - `GameTooManyClickError`: Click loop detected, restart task

2. **Fatal Errors** (exit script):
   - `RequestHumanTakeover`: Manual intervention required
   - All uncaught exceptions

3. **Flow Control:**
   - `TaskEnd`: Normal task completion
   - `ProcessComplete`: Stage completion (e.g., all guild battles done)

**Usage Pattern:**

```python
from module.exception import GameStuckError, GameNotRunningError, RequestHumanTakeover

def some_handler_method(self):
    # Use GameStuckError for unexpected states
    if self.appear(UNEXPECTED_ERROR_POPUP):
        raise GameStuckError("Unexpected error popup appeared")

    # Use GameNotRunningError if game crashed
    if not self.device.app_is_running():
        raise GameNotRunningError("App crashed during battle")

    # Use RequestHumanTakeover for cases requiring human decision
    if self.appear(PAYMENT_REQUIRED):
        raise RequestHumanTakeover("Payment required, human intervention needed")

    # Use TaskEnd for successful completion
    if self.appear(TASK_COMPLETE):
        raise TaskEnd("Task completed successfully")
```

**Common mistakes:**

```python
# ❌ WRONG: Rapid clicking without interval
while True:
    self.device.screenshot()
    if self.appear(BUTTON):
        self.device.click(BUTTON)  # Will click every loop → GameTooManyClickError

# ✅ CORRECT: Use interval parameter
while True:
    self.device.screenshot()
    if self.appear(BUTTON, interval=1.0):  # Only clicks once per second
        self.device.click(BUTTON)
```

## How to access configuration

**[SKILL] Safe configuration access pattern**

**Config Structure:**
- Config files: `config/*.json` (e.g., `config/maple.json`)
- Generated class: `GeneratedConfig` (auto-generated from template)
- Main class: `PriconneConfig` (inherits GeneratedConfig)
- Access pattern: Use dot notation for config keys

**Important:**
- Config uses GeneratedConfig, so all keys have IntelliSense
- Config files are JSON, but accessed as Python attributes
- Use config watcher for hot-reload during development

**Usage:**

```python
# In a Handler or Module:
def use_config_safely(self):
    # Access config (already injected via self.config)
    screenshot_method = self.config.Emulator_ScreenshotMethod  # "DroidCast_Raw"
    control_method = self.config.Emulator_ControlMethod  # "MaaTouch"

    # Check boolean configs
    if self.config.Enable_SomeFeature:
        self.do_something()

    # Access nested configs
    server = self.config.Server  # "国服" or "B服"

# In pcr.py (scheduler):
from module.config.config import PriconneConfig

config = PriconneConfig(config_name="maple")  # Loads config/maple.json
```

## How to run and create tests

**[SKILL] How to run and create tests in this project**

**Important: This project does NOT use pytest!**
- Tests are standalone Python scripts in `tests/`
- Run them directly: `python tests/test_xxx.py`
- Many tests support flags (e.g., `--droidcast`)

**Running Tests:**

```bash
# Run a specific test
python tests/test_battle_train.py

# Run with DroidCast screenshot method
python tests/test_battle_train.py --droidcast

# Run screenshot benchmark
python tests/test_screenshot_benchmark.py
```

**Creating New Tests:**

1. Create test file in `tests/` directory
2. Import required modules
3. Set up test config and device
4. Write test logic
5. Add argparse for flags (optional)

**Example Test:**

```python
# tests/test_new_feature.py
import sys
sys.path.insert(0, '..')

from module.config.config import PriconneConfig
from module.device.device import Device
from module.handler.new_feature import NewFeatureHandler

def test_new_feature():
    config = PriconneConfig(config_name='template')
    device = Device(config=config)
    handler = NewFeatureHandler(config=config, device=device)

    try:
        handler.run()
        print("✅ Test passed")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise

if __name__ == '__main__':
    test_new_feature()
```

## How to use git workflow

**[SKILL] Git workflow for AI development**

**Branching Strategy:**
- `main`: Stable code, human-verified
- `ai-dev-{feature}`: AI working branches
- AI works on `ai-dev-*` branches
- Human reviews and merges to main

**Commit Pattern:**

```bash
# After completing a task from TODO.md:

# 1. Check status
git status

# 2. Add changed files (be specific, avoid git add .)
git add module/handler/new_feature.py
git add assets/new_feature/BUTTON.png
git add tests/test_new_feature.py

# 3. Commit with descriptive message
git commit -m "feat: implement new feature handler

- Add NewFeatureHandler with main flow
- Create button definitions for feature UI
- Add test coverage for happy path

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# 4. Push to AI branch
git push origin ai-dev-new-feature

# 5. Update TODO.md (mark task as complete)
# 6. Update DEV_LOG.md (record outcome and learnings)
```

**DO NOT:**
- Force push (`git push -f`)
- Commit to main directly
- Use `git add .` or `git add -A` (may include sensitive files)
- Skip the co-authored-by line
- Amend commits after push

**DO:**
- Use descriptive commit messages
- Add specific files by path
- Keep commits focused (one logical change)
- Update TODO.md after each commit
- Record learnings in DEV_LOG.md

## How to manage dependencies

**[SKILL] Managing Python dependencies**

**Rules:**
1. ONLY use libraries already in `requirements.txt`
2. If new library is absolutely necessary:
   a. Update `requirements.txt`
   b. Document why it's needed in `DEV_LOG.md`
   c. Notify human for approval
   d. Wait for approval before using it

**Installing Dependencies:**

```bash
# Fresh install
pip install -r requirements.txt

# Check current dependencies
pip list
```

**If you need a new library:**

```bash
# ❌ DON'T: Just pip install and use it
pip install new-library
import new_library

# ✅ DO: Update requirements.txt and ask for approval

# 1. Add to requirements.txt:
echo "new-library==1.2.3  # Reason: needed for XYZ feature" >> requirements.txt

# 2. Document in DEV_LOG.md:
```

```markdown
## New Dependency Request

**Library:** new-library==1.2.3
**Reason:** Current OCR library doesn't support feature X, which is required for Y
**Alternatives considered:**
- Alternative A: Doesn't support Python 3.7
- Alternative B: 10x slower performance

**Waiting for human approval before proceeding.**
```

```bash
# 3. Ask human via TODO.md or raise RequestHumanTakeover
```

## Quick Reference

**Creating Buttons:** Always use `python dev_tools/create_button.py`

**Detection Pattern:**
```python
self.device.screenshot()
if self.appear(BUTTON, interval=1.0):
    self.device.click(BUTTON)
```

**Handler Structure:** `UI → navigation methods → screenshot → detect → act`

**Exception Handling:**
- Recoverable: `GameStuckError`, `GameNotRunningError`, `GameTooManyClickError`
- Fatal: `RequestHumanTakeover`
- Flow: `TaskEnd`, `ProcessComplete`

**Git Workflow:** Work on `ai-dev-*` branch → commit → push → update TODO/DEV_LOG

**Dependencies:** Only use `requirements.txt` libraries, ask before adding new ones

**Testing:** Run directly with `python tests/test_xxx.py` (NOT pytest)

**Architecture Layers:** Config → Device → Base → UI → Handler → Scheduler
