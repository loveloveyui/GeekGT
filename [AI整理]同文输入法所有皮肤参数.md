---
title: Trime（同文输入法）皮肤配置参数完整说明与源码交叉验证
date: 2026-11-15
tags:
  - Trime
  - 同文输入法
  - 皮肤主题
  - 参数手册
  - 源码审计
---

# Trime（同文输入法）皮肤配置参数完整说明与源码交叉验证

> [!INFO] 核查基准
> 本文档基于 `/root/codes/trime`（`develop` 分支）编制，将官方配置文档（`doc/trime-schema.json`、`doc/Keyboard.md`）与实际 Kotlin 运行时反序列化源码（`app/src/main/java/com/osfans/trime/data/theme/`）进行了逐字段交叉验证。
> 所有 YAML 键名均通过 `YamlNamingStrategy.SnakeCase` 自动映射，使用**全小写下划线命名（`snake_case`）**。

---

## 第一部分：文档与源码交叉验证差异汇总

> [!WARNING] 为什么不能只看 `doc/trime-schema.json`？
> 官方 `trime-schema.json` 更新滞后，存在**字段已改名、层级已调整、旧字段已废弃、新增字段未收录**等问题。直接照搬 Schema 编写皮肤会导致部分配置静默失效。

### 1.1 `tool_bar` 重大不兼容差异（`ToolBar.kt` vs Schema）

| 位置 | Schema 文档写法 | 实际 Kotlin 源码写法 | 影响说明 |
| :--- | :--- | :--- | :--- |
| `Button.background` | `bg_normal` / `bg_highlight` | **`normal`** / **`highlight`** | 写 `bg_normal` 不会生效 |
| `Button.foreground` | `fg_normal` / `fg_highlight` | **`normal`** / **`highlight`** | 写 `fg_normal` 不会生效 |
| `Button.size` 所属层级 | 放在 `foreground` 内 | **直接放在 `Button` 顶层** | 放在 `foreground` 内无法解析 |
| `ToolBar.back_style` | 文档未提及 | **代码新增**：`back_style`（默认 `"ic@arrow-left"`） | 控制工具栏返回图标样式 |
| `Button.long_press_action` | 文档未提及 | **代码新增**：`long_press_action` | 支持为工具栏按钮配置长按动作 |

### 1.2 `style` 字段差异（`GeneralStyle.kt` vs Schema）

* **文档中有，但代码中已移除/改名（8 项）**：
  * `comment_on_top` → 已替换为 **`comment_position`**（`RIGHT` \| `TOP` \| `OVERLAY`）
  * `keyboards` → 已移出 `style`，统一由顶层 **`preset_keyboards`** 管理
  * `preview_font` → 已替换为 **`popup_font`**
  * `preview_height` → 已替换为 **`popup_height`** / **`popup_key_height`**
  * `preview_offset` → 已替换为 **`popup_bottom_margin`**
  * `preview_text_size` → 已替换为 **`popup_text_size`**
  * `proximity_correction` → 代码中已移除
  * `vertical_correction` → 代码中已移除

* **代码中有，但文档未提及（23 项）**：
  * **候选栏与提示**：`candidate_border`、`candidate_border_round`、`candidate_corner_radius`、`candidate_text_vertical_bias`、`comment_position`、`comment_vertical_bias`
  * **按键与字体**：`key_border`、`key_long_text_size`、`text_font`
  * **按键文字微调偏移**：`key_text_offset_x`、`key_text_offset_y`、`key_symbol_offset_x`、`key_symbol_offset_y`、`key_hint_offset_x`、`key_hint_offset_y`、`key_press_offset_x`、`key_press_offset_y`
  * **按键气泡弹窗（Popup）**：`popup_bottom_margin`、`popup_width`、`popup_height`、`popup_key_height`、`popup_font`、`popup_text_size`

### 1.3 `liquid_keyboard` 字段差异（`LiquidKeyboard.kt` vs Schema / `Keyboard.md`）

* **文档中有，但代码中不存在（5 项）**：`author`、`key_height_land`、`row`、`row_land`、`vertical_gap`。
* 代码实际支持的字段为：`single_width`、`key_height`、`margin_x`、`fixed_key_bar`、`keyboards`。

### 1.4 颜色键与默认值差异（`ColorKey.kt`、`Preedit.kt`、`Window.kt` vs Schema）

* **文档中有，但代码中已移除（2 项）**：`preview_back_color`、`preview_text_color`（已改名为 `popup_back_color`、`popup_text_color`）。
* **代码中有，但 Schema `fallback_colors` 未收录（10 项）**：
  * 基础终结点：`back_color`、`text_color`
  * 新增带回退链的颜色键：`candidate_border_color`、`hilited_candidate_button_color`、`hilited_popup_back_color`、`hilited_popup_text_color`、`keyboard_background`、`long_text_color`、`popup_back_color`、`popup_text_color`
* **默认值差异**：
  * `preedit.alpha`：代码默认 **`0.8f`**（Schema 写 `1.0`）
  * `window.insets`：代码默认 **`4, 4`**（Schema 写 `0, 0`）
  * `window.item_padding`：代码默认 **`vertical: 2, horizontal: 4`**（Schema 写 `0, 0`）
  * `window.foreground.comment_font_size`：代码默认 **`20f`**（Schema 写 `16`）
* **顶层元数据键**：代码 `Theme.TOP_LEVEL_KEYS` 额外允许 **`description`** 与 **`version`**（Schema 未列）；其余未在 `TOP_LEVEL_KEYS` 列表中的顶层键会被运行时忽略并被 `ThemeDiagnostics` 报错。

---

## 第二部分：全量皮肤配置参数中文手册（基于源码核对）

### 一、顶层配置键（`Theme.kt`）与 DSL 规则

| 参数名 | 类型 | 必填 | 中文说明 |
| :--- | :--- | :---: | :--- |
| `name` | String | 是 | 主题显示名称 |
| `config_version` | String | 否 | 配置格式版本标识 |
| `author` | String | 否 | 主题作者信息 |
| `description` | String | 否 | 主题描述（代码支持，Schema 未列） |
| `version` | String | 否 | 主题版本号（代码支持，Schema 未列） |
| `style` | Object | 否 | 全局样式配置（字体、尺寸、间距、偏移等） |
| `preedit` | Object | 否 | 预编辑区（拼音串/编码栏）样式 |
| `window` | Object | 否 | 悬浮候选窗样式（如横屏或光标跟随候选窗） |
| `tool_bar` | Object | 否 | 顶部工具栏按钮与图标配置 |
| `liquid_keyboard` | Object | 否 | 液态键盘（符号、剪贴板、草稿箱等扩展面板） |
| `preset_keys` | Map | 否 | 预设按键动作字典（供键盘按键引用） |
| `preset_keyboards` | Map | 否 | 键盘布局定义集合（如默认26键、九宫格、数字键盘） |
| `preset_color_schemes` | Map | 否 | 配色方案集合（支持多套亮色/暗色切换） |
| `fallback_colors` | Map | 否 | 自定义颜色回退链（覆盖内置回退规则） |

> [!TIP] `ThemeDslExpander` 语法限制
> 直接加载源码 YAML 时，仅支持 `__include: /本地路径` 或 `file:/路径`（末尾可加 `?` 表示可选）、同级键覆盖、以及 `__patch: /路径` 或 `{ key: value }`。不支持 `__merge`、include 列表或 `/+`、`/=` 路径操作符。

---

### 二、全局样式 `style`（`GeneralStyle.kt`）

#### 2.1 键盘尺寸、边距与行为

| 参数名 | 类型 | 默认值 | 中文说明 |
| :--- | :--- | :--- | :--- |
| `auto_caps` | Boolean? | `false` | 是否开启英文句首自动大写 |
| `reset_ascii_mode_on_focus_change` | Boolean | `false` | 切换输入框焦点时是否重置中英文状态 |
| `background_folder` | String | `"backgrounds"` | 主题背景图片存放的子文件夹名称 |
| `keyboard_height` | Int | `0` | 竖屏时键盘整体高度（dp） |
| `keyboard_height_land` | Int | `0` | 横屏时键盘整体高度（dp） |
| `keyboard_padding` | Int | `0` | 键盘整体内边距（上下左右通用基值） |
| `keyboard_padding_left` | Int | `0` | 键盘左侧内边距 |
| `keyboard_padding_right` | Int | `0` | 键盘右侧内边距 |
| `keyboard_padding_bottom` | Int | `0` | 竖屏键盘底部内边距 |
| `keyboard_padding_land` | Int | `0` | 横屏键盘左右内边距 |
| `keyboard_padding_land_bottom` | Int | `0` | 横屏键盘底部内边距 |
| `horizontal_gap` | Int | `0` | 按键之间的水平间距 |
| `vertical_gap` | Int | `0` | 按键行之间的垂直间距 |

#### 2.2 按键外观、字体与文字偏移

| 参数名 | 类型 | 默认值 | 中文说明 |
| :--- | :--- | :--- | :--- |
| `key_width` | Float | `0f` | 默认按键宽度百分比（如 `10` 表示占一行宽度的 10%） |
| `key_height` | Int | `0` | 默认单行按键高度 |
| `key_border` | Int | `0` | 按键边框宽度 |
| `round_corner` | Float | `0f` | 按键圆角半径 |
| `shadow_radius` | Float | `0f` | 按键阴影半径 |
| `key_text_size` | Float | `15f` | 按键主字符字号 |
| `key_long_text_size` | Float | `15f` | 按键长按字符/提示字号 |
| `label_text_size` | Float | `0f` | 辅助标签字号 |
| `symbol_text_size` | Float | `0f` | 按键右上角/副符号字号 |
| `key_font` | String / List | 空 | 按键主字符字体（支持单字体或字体回退列表） |
| `label_font` | String / List | 空 | 辅助标签字体 |
| `symbol_font` | String / List | 空 | 按键符号字体 |
| `latin_font` | String / List | 空 | 拉丁字母回退字体 |
| `hanb_font` | String / List | 空 | 中日韩扩展 B 区生僻字回退字体 |
| `text_font` | String / List | 空 | 通用文本字体 |
| `key_text_offset_x` / `y` | Float | `0f` | 按键主字符水平/垂直微调偏移量 |
| `key_symbol_offset_x` / `y` | Float | `0f` | 按键副符号水平/垂直微调偏移量 |
| `key_hint_offset_x` / `y` | Float | `0f` | 按键 Hint 提示水平/垂直微调偏移量 |
| `key_press_offset_x` / `y` | Float | `0f` | 按键按下状态时的视觉位移偏移量 |

#### 2.3 候选栏、注释与回车键

| 参数名 | 类型 | 默认值 | 中文说明 |
| :--- | :--- | :--- | :--- |
| `candidate_view_height` | Int | `28` | 候选栏高度 |
| `candidate_padding` | Int | `0` | 单个候选词左右内边距 |
| `candidate_spacing` | Float | `0f` | 候选词之间的间隔 |
| `candidate_border` | Int | `0` | 候选词边框宽度 |
| `candidate_border_round` | Float | `0f` | 候选词边框圆角 |
| `candidate_corner_radius` | Float | `5f` | 选中/高亮候选词背景圆角半径 |
| `candidate_text_size` | Float | `15f` | 候选词字号 |
| `candidate_text_vertical_bias` | Float | `1f` | 候选词垂直对齐权重（`0` 靠上，`1` 居中/靠下） |
| `candidate_font` | String / List | 空 | 候选词字体 |
| `comment_height` | Int | `12` | 候选词注释（如辅助码提示）区域高度 |
| `comment_text_size` | Float | `10f` | 候选词注释字号 |
| `comment_position` | Enum | `RIGHT` | 注释位置：`RIGHT`（右侧）、`TOP`（上方）、`OVERLAY`（覆盖） |
| `comment_vertical_bias` | Float | `0f` | 注释文字垂直对齐权重 |
| `comment_font` | String / List | 空 | 候选词注释字体 |
| `enter_label_mode` | Int | `0` | 回车键动态标签模式 |
| `enter_labels` | Object | 见右 | 各场景回车键显示文字：`go`、`done`、`next`、`pre`、`search`、`send`、`default` |

#### 2.4 按键气泡弹窗（Popup）

| 参数名 | 类型 | 默认值 | 中文说明 |
| :--- | :--- | :--- | :--- |
| `popup_bottom_margin` | Int | `0` | 按键放大气泡距离按键底部的边距 |
| `popup_width` | Int | `0` | 气泡弹窗宽度 |
| `popup_height` | Int | `0` | 气泡弹窗高度 |
| `popup_key_height` | Int | `0` | 气泡内候选子按键的高度 |
| `popup_text_size` | Float | `0f` | 气泡内文字字号 |
| `popup_font` | String / List | 空 | 气泡内文字字体 |

---

### 三、预编辑区 `preedit`（`Preedit.kt`）与悬浮窗 `window`（`Window.kt`）

#### 3.1 `preedit`（输入编码预览栏）

| 参数名 | 类型 | 默认值 | 中文说明 |
| :--- | :--- | :--- | :--- |
| `horizontal_padding` | Int | `8` | 预编辑区左右内边距 |
| `top_start_radius` | Float | `0f` | 左上角圆角半径 |
| `top_end_radius` | Float | `0f` | 右上角圆角半径 |
| `alpha` | Float | `0.8f` | 背景透明度（`0.0`–`1.0`） |
| `foreground.font_size` | Float | `16f` | 预编辑编码文字字号 |

#### 3.2 `window`（悬浮候选窗）

| 参数名 | 类型 | 默认值 | 中文说明 |
| :--- | :--- | :--- | :--- |
| `insets` | Object | `{vertical: 4, horizontal: 4}` | 悬浮窗整体外边距/内缩留白 |
| `item_padding` | Object | `{vertical: 2, horizontal: 4}` | 单个候选条目内边距 |
| `min_width` | Int | `0` | 悬浮窗最小宽度 |
| `corner_radius` | Float | `0f` | 悬浮窗圆角半径 |
| `border` | Int | `0` | 悬浮窗边框宽度 |
| `shadow` | Float | `0f` | 悬浮窗阴影大小 |
| `alpha` | Float | `1f` | 悬浮窗整体透明度 |
| `foreground.label_font_size` | Float | `20f` | 候选序号（1, 2, 3...）字号 |
| `foreground.text_font_size` | Float | `20f` | 候选词字号 |
| `foreground.comment_font_size` | Float | `20f` | 候选注释字号 |

---

### 四、工具栏 `tool_bar`（`ToolBar.kt`）

| 参数名 | 类型 | 默认值 | 中文说明 |
| :--- | :--- | :--- | :--- |
| `primary_button` | Button | `null` | 工具栏左侧主按钮（通常为同文徽标或主菜单入口） |
| `buttons` | List\<Button\> | `[]` | 工具栏右侧功能按钮列表 |
| `button_spacing` | Int | `18` | 按钮之间的水平间距 |
| `button_font` | String / List | 空 | 工具栏按钮文字/图标字体 |
| `back_style` | String | `"ic@arrow-left"` | 返回按钮图标样式 |

**单个 `Button` 对象参数**：

| 参数路径 | 类型 | 默认值 | 中文说明 |
| :--- | :--- | :--- | :--- |
| `action` | String | `""` | 点击按钮触发的动作（对应 `preset_keys` 名称或内置指令） |
| `long_press_action` | String | `""` | 长按按钮触发的动作（代码新增） |
| `size` | List\<Int\> | `[]` | 按钮宽高尺寸，如 `[36, 36]`（注意位于 Button 顶层） |
| `background.type` | Enum | `RECTANGLE` | 背景形状：`RECTANGLE`（矩形）或 `CIRCLE`（圆形） |
| `background.corner_radius` | Float | `10f` | 矩形背景圆角半径 |
| `background.normal` | String | `""` | 常态背景颜色键名或色值 |
| `background.highlight` | String | `""` | 按下/高亮背景颜色键名或色值 |
| `background.vertical_inset` | Int | `4` | 背景垂直内缩边距 |
| `background.horizontal_inset` | Int | `4` | 背景水平内缩边距 |
| `foreground.style` | String | `""` | 前景图标/文字样式（如 `ic@settings` 或文字） |
| `foreground.option_styles` | List\<String\> | `[]` | 跟随 Rime option 状态切换的多态图标/文字列表 |
| `foreground.normal` | String | `""` | 常态前景颜色键名或色值 |
| `foreground.highlight` | String | `""` | 按下/高亮前景颜色键名或色值 |
| `foreground.font_size` | Float | `18f` | 前景文字或图标字号 |
| `foreground.padding` | Int | `4` | 前景内边距 |

---

### 五、液态键盘 `liquid_keyboard`（`LiquidKeyboard.kt`）

| 参数名 | 类型 | 默认值 | 中文说明 |
| :--- | :--- | :--- | :--- |
| `single_width` | Int | `0` | `SINGLE` 类型面板中每个格子的宽度（与高度相等） |
| `key_height` | Int | `0` | 液态键盘按键行高 |
| `margin_x` | Float | `0f` | 液态键盘左右边距 |
| `fixed_key_bar.position` | Enum | `BOTTOM` | 固定按键条摆放位置：`TOP`、`BOTTOM`、`LEFT`、`RIGHT` |
| `fixed_key_bar.keys` | List\<String\> | `[]` | 固定按键条内的按键列表（引用 `preset_keys` 键名） |
| `keyboards` | List\<Keyboard\> | `[]` | 液态键盘标签页列表，每项包含 `id`、`name`、`type`、`keys` |

**`keyboards[].keys[]`（`KeyItem`）字段**：
* `text`（String）：按键主显示与上屏文本
* `alt_text`（String）：备用/长按文本

**`keyboards[].type`（`DataType`）源码实际支持的 4 种类型**：
* `SINGLE`（单格等宽，宽度受 `single_width` 控制）
* `SYMBOL`（符号面板，注意为单数 `SYMBOL`）
* `TABS`（标签导航页，自动聚合非 `TABS` 面板名称作为跳转项）
* `HISTORY`（历史记录面板；剪贴板、草稿箱、收藏夹等现已独立为内置系统面板，不再属于 `DataType` 枚举）

---

### 六、预设按键 `preset_keys`（`PresetKey.kt`）

每个预设按键条目支持以下 16 个属性：

| 参数名 | 类型 | 默认值 | 中文说明 |
| :--- | :--- | :--- | :--- |
| `label` | String | `""` | 按键上显示的文字 |
| `preview` | String? | `null` | 按下气泡中显示的预览文字 |
| `send` | String | `""` | 发送的键值（如 `BackSpace`、`Return`、`space`、`Shift_L`） |
| `commit` | String | `""` | 直接上屏的字符串 |
| `text` | String | `""` | 发送到 Rime 引擎处理的输入序列（支持 `{key}` 语法） |
| `command` | String | `""` | 执行内置命令（如 `liquid_keyboard`、`settings`、`theme`） |
| `option` | String | `""` | 命令附带参数（如切换的 `liquid_keyboard` 标签名） |
| `select` | String | `""` | 切换到的键盘布局 ID（对应 `preset_keyboards` 中的键） |
| `toggle` | String | `""` | 切换的 Rime 开关名（如 `ascii_mode`、`simplification`） |
| `states` | List\<String\> | `[]` | 配合 `toggle` 使用的多状态显示标签列表 |
| `shift_lock` | String | `""` | 大写锁定模式：`long`（长按锁定）、`click`（点击锁定）、`ascii_long` |
| `sticky` | Boolean | `false` | 是否为粘滞键（如 Shift 修饰状态保持） |
| `repeatable` | Boolean | `false` | 长按时是否连续重复触发（常用于退格、方向键） |
| `slide_cursor` | Boolean | `false` | 是否支持左右滑动移动光标（常用于空格键） |
| `slide_delete` | Boolean | `false` | 是否支持滑动删除（常用于退格键） |
| `functional` | Boolean | `false` | 是否为功能键（决定是否应用功能键的 `off/on` 配色） |

---

### 七、键盘布局 `preset_keyboards` 与单键 `keys`（`TextKeyboard.kt`）

#### 7.1 键盘级参数（`TextKeyboard`，共 29 项）

| 参数名 | 类型 | 默认值 | 中文说明 |
| :--- | :--- | :--- | :--- |
| `name` | String | `""` | 键盘布局名称 |
| `author` | String | `""` | 键盘布局作者 |
| `width` / `height` | Float | `0f` | 键盘默认单键宽（%）与行高 |
| `keyboard_height` / `_land` | Int | `0` | 覆盖全局的竖屏/横屏键盘高度 |
| `auto_height_index` | Int | `-1` | 自动高度计算参考行索引 |
| `horizontal_gap` / `vertical_gap` | Int | `0` | 覆盖全局的水平/垂直键距 |
| `round_corner` | Float | `-1f` | 覆盖全局的圆角半径（`-1` 表示继承全局） |
| `key_border` | Int | `-1` | 覆盖全局的边框宽度（`-1` 表示继承全局） |
| `columns` | Int | `30` | 网格布局列数基数（用于自动均分宽度） |
| `ascii_mode` | Int | `1` | 该键盘默认的 ASCII 状态（`1` 英文，`0` 中文） |
| `reset_ascii_mode` | Boolean | `false` | 切换到此键盘时是否强制重置中英文状态 |
| `label_transform` | Enum | `NONE` | 字母大小写显示转换：`NONE`（不转换）、`UPPERCASE`（全大写） |
| `lock` | Boolean | `false` | 是否锁定当前键盘（不随输入状态自动切走） |
| `ascii_keyboard` | String | `""` | 英文状态下自动切换的目标键盘 ID |
| `landscape_keyboard` | String | `""` | 横屏时自动切换的目标键盘 ID |
| `landscape_split_percent` | Int | `0` | 横屏分体键盘中间留白比例（`0`–`200`，`0` 为不分体） |
| `import_preset` | String | `""` | 继承/导入另一个键盘的预设（切勿形成循环引用） |
| `key_*_offset_x/y`（8项） | Float | `0f` | 键盘级 `text`/`symbol`/`hint`/`press` 的 X/Y 偏移覆盖 |
| `keys` | List\<TextKey\> | `[]` | 按键定义列表 |

#### 7.2 单键级参数（`TextKey`，共 38 项）

* **几何与文字**：`width`（`0f`）、`height`（`0f`）、`round_corner`（`-1f`）、`key_border`（`-1`）、`label`、`label_symbol`、`hint`、`send_bindings`（默认 `true`，是否在编码/菜单状态下启用绑定动作）、`key_text_size`、`symbol_text_size`、`popup`（长按弹出候选字符列表）、以及 8 个单键级 `key_*_offset_x/y` 偏移覆盖。
* **单键颜色覆盖（8 项）**：`key_text_color`、`key_back_color`、`key_border_color`、`key_symbol_color`、`hilited_key_text_color`、`hilited_key_back_color`、`hilited_key_border_color`、`hilited_key_symbol_color`。
* **触发动作（13 种事件，支持 `preset_keys` 名称或内联 `{ commit, text, label }` 对象）**：
  * 触控手势：`click`（单击）、`double_click`（双击）、`lazy_double_click`（延迟双击）、`long_click`（长按）、`swipe_up`（上滑）、`swipe_down`（下滑）、`swipe_left`（左滑）、`swipe_right`（右滑）。
  * 上下文状态联动：`composing`（正在输入编码时）、`has_menu`（存在候选菜单时）、`paging`（候选翻页时）、`combo`（组合键）、`ascii`（英文模式下）。

---

### 八、颜色体系 `preset_color_schemes` 与回退链（`ColorKey.kt`）

Trime 运行时共定义了 **52 个规范颜色键**。当某个配色方案未显式指定某个颜色键时，系统会沿内置回退链逐级查找（直到 `back_color` 或 `text_color` 等终结点）：

| 分组 | 规范颜色键名 | 内置默认回退目标 | 中文说明 |
| :--- | :--- | :--- | :--- |
| **全局底色与边框** | `back_color` | *(终结点)* | 全局基础背景色 |
| | `text_color` | *(终结点)* | 全局基础文字色 |
| | `border_color` | `back_color` | 全局边框色 |
| | `shadow_color` | `border_color` | 阴影颜色 |
| | `root_background` | `back_color` | 输入法根视图背景（支持图片或色值） |
| | `keyboard_back_color` | `border_color` | 键盘区背景底色 |
| | `keyboard_background` | `keyboard_back_color` | 键盘区背景（支持图片或色值，文档未列） |
| | `liquid_keyboard_background` | `keyboard_back_color` | 液态键盘区域背景 |
| | `text_back_color` | `back_color` | 预编辑文本背景色 |
| **高亮基础** | `hilited_back_color` | `back_color` | 高亮状态通用背景 |
| | `hilited_text_color` | `text_color` | 高亮状态通用文字（如已选编码） |
| | `hilited_label_color` | `hilited_candidate_text_color` | 高亮候选序号颜色 |
| | `hilited_comment_text_color` | `comment_text_color` | 高亮候选注释文字颜色 |
| **候选栏** | `candidate_background` | `back_color` | 候选栏整体背景 |
| | `candidate_border_color` | *(无内置链)* | 候选词边框颜色（文档未列） |
| | `candidate_separator_color` | `border_color` | 候选词分隔线颜色 |
| | `candidate_text_color` | `text_color` | 普通候选词文字颜色 |
| | `comment_text_color` | `candidate_text_color` | 普通候选注释文字颜色 |
| | `label_color` | `candidate_text_color` | 普通候选序号颜色 |
| | `hilited_candidate_back_color` | `hilited_back_color` | 选中候选词背景色 |
| | `hilited_candidate_button_color` | `hilited_candidate_back_color` | 高亮候选按钮背景色（文档未列） |
| | `hilited_candidate_text_color` | `hilited_text_color` | 选中候选词文字颜色 |
| **常规按键** | `key_back_color` | `back_color` | 普通按键背景色 |
| | `key_border_color` | `border_color` | 普通按键边框色 |
| | `key_text_color` | `candidate_text_color` | 普通按键主文字颜色 |
| | `key_symbol_color` | `comment_text_color` | 普通按键副符号颜色 |
| | `hilited_key_back_color` | `hilited_candidate_back_color` | 按下按键背景色 |
| | `hilited_key_border_color` | `key_border_color` | 按下按键边框色 |
| | `hilited_key_text_color` | `hilited_candidate_text_color` | 按下按键主文字颜色 |
| | `hilited_key_symbol_color` | `hilited_comment_text_color` | 按下按键副符号颜色 |
| | `long_text_color` | `key_text_color` | 长按提示文字颜色（文档未列） |
| | `long_text_back_color` | `key_back_color` | 长按提示背景颜色 |
| **功能键（Off 常态）** | `off_key_back_color` | `key_back_color` | 功能键关闭状态背景色 |
| | `off_key_border_color` | `key_border_color` | 功能键关闭状态边框色 |
| | `off_key_text_color` | `key_text_color` | 功能键关闭状态文字色 |
| | `off_key_symbol_color` | `key_symbol_color` | 功能键关闭状态符号色 |
| **功能键（Off 按下）** | `hilited_off_key_back_color` | `hilited_key_back_color` | 功能键关闭且按下背景色 |
| | `hilited_off_key_border_color` | `hilited_key_border_color` | 功能键关闭且按下边框色 |
| | `hilited_off_key_text_color` | `hilited_key_text_color` | 功能键关闭且按下文字色 |
| | `hilited_off_key_symbol_color` | `hilited_key_symbol_color` | 功能键关闭且按下符号色 |
| **功能键（On 常态）** | `on_key_back_color` | `hilited_key_back_color` | 功能键开启/锁定背景色 |
| | `on_key_border_color` | `hilited_key_border_color` | 功能键开启/锁定边框色 |
| | `on_key_text_color` | `hilited_key_text_color` | 功能键开启/锁定文字色 |
| | `on_key_symbol_color` | `hilited_key_symbol_color` | 功能键开启/锁定符号色 |
| **功能键（On 按下）** | `hilited_on_key_back_color` | `hilited_key_back_color` | 功能键开启且按下背景色 |
| | `hilited_on_key_border_color` | `hilited_key_border_color` | 功能键开启且按下边框色 |
| | `hilited_on_key_text_color` | `hilited_key_text_color` | 功能键开启且按下文字色 |
| | `hilited_on_key_symbol_color` | `hilited_key_symbol_color` | 功能键开启且按下符号色 |
| **气泡弹窗（Popup）** | `popup_back_color` | `key_back_color` | 按键弹出气泡背景色（文档未列） |
| | `popup_text_color` | `key_text_color` | 按键弹出气泡文字色（文档未列） |
| | `hilited_popup_back_color` | `hilited_key_back_color` | 气泡内高亮选中项背景色（文档未列） |
| | `hilited_popup_text_color` | `hilited_key_text_color` | 气泡内高亮选中项文字色（文档未列） |
