### 一、`processors`



- 這批組件處理各類按鍵消息

1. `ascii_composer` 處理西文模式及中西文切換

   配置示例：
   ```yaml
   ascii_composer:
     good_old_caps_lock: true  # true: CapsLock切换大写; false: CapsLock切换中英
     switch_key:
       Caps_Lock: clear        # 清除未上屏内容后切换到英文
       Shift_L: commit_code    # 上屏原始编码后切换到英文
       Shift_R: noop           # 屏蔽，不切换中英
       Control_L: noop
       Control_R: noop
   ```

   效果演示：
   - 输入 `nihao`（尚未上屏），按下 `Caps_Lock`: 清除 `nihao`，切换为英文模式，键盘输入直接上屏字母。
   - 输入 `nihao`（尚未上屏），按下左 `Shift`: 将 `nihao` 作为原始编码上屏，然后切换为英文模式。
   - `good_old_caps_lock: true`（默认）: 按 CapsLock 切换字母大小写，不改变中英文状态。
   - `good_old_caps_lock: false`: 按 CapsLock 切换中英文输入状态。
   - `inline_ascii`: 临时英文模式，输入完回车后自动回到中文。适合偶尔输入一个英文词。
2. **`recognizer`** 與`matcher`搭配，處理符合特定規則的輸入碼，如網址、反查等`tags`

   配置示例：
   ```yaml
   recognizer:
     import_preset: default    # 从 default.yaml 继承通用规则
     patterns:                 # 增加方案专有规则
       punct: "^v([0-9]|10|[A-Za-z]+)$"   # 以 v 开头的符号输入
       radical_lookup: "^uU[a-z]+$"        # 以 uU 开头的部件拆字反查
       unicode: "^U[a-f0-9]+"              # 以 U 开头的 Unicode 码
       number: "^R[0-9]+[.]?[0-9]*"        # 以 R 开头的数字金额大写
       calculator: "^cC.+"                 # 以 cC 开头的计算器
       gregorian_to_lunar: "^N[0-9]{1,8}"  # 以 N 开头的公历转农历
   ```

   效果演示：
   - 输入 `v1`: 触发 `punct` 规则，给这段输入加上 `punct` tag，后续由 `punct_translator` 处理成符号。
   - 输入 `U4e2d`: 触发 `unicode` 规则，由 `lua_translator@*unicode` 输出对应 Unicode 字符"中"。
   - 输入 `R1234.56`: 触发 `number` 规则，由 `lua_translator@*number_translator` 输出"一千二百三十四元五角六分"。
   - 输入 `cC1+2`: 触发 `calculator` 规则，由 `lua_translator@*calc_translator` 输出计算结果。
   - 通用 patterns（从 default 继承）包括 email 识别（`xxx@xxx` 不自动上屏）、网址识别（`https://...`）等。
3. **`key_binder`** 在特定條件下將按鍵綁定到其他按鍵，如重定義逗號、句號爲候選翻頁、開關快捷鍵等

   配置示例：
   ```yaml
   key_binder:
     import_preset: default         # 从 default.yaml 继承通用快捷键
     select_first_character: "bracketleft"   # [ 键：以词定字（取首字）
     select_last_character: "bracketright"   # ] 键：以词定字（取末字）
     bindings:
       # Tab / Shift+Tab 切换光标至下/上一个拼音
       - { when: composing, accept: Shift+Tab, send: Shift+Left }
       - { when: composing, accept: Tab, send: Shift+Right }
       # - = 翻页
       - { when: has_menu, accept: minus, send: Page_Up }
       - { when: has_menu, accept: equal, send: Page_Down }
       # 开关快捷键
       - { when: always, toggle: ascii_punct, accept: Control+Shift+3 }
       - { when: always, toggle: traditionalization, accept: Control+Shift+4 }
   ```

   效果演示：
   - 输入 `zhongguo` 出现候选"中国"，按 `[`：上屏"中"（首字）；按 `]`：上屏"国"（末字）。
   - 候选项出现后，按 `-` 向前翻页，按 `=` 向后翻页。
   - 按 `Control+Shift+4`：切换简繁开关，候选项立即变为繁体/简体。
   - `when: composing` 仅在编辑中生效，`when: has_menu` 仅在候选菜单显示时生效，`when: always` 始终生效。
   - 可自定义：将逗号句号改为翻页 `{ when: has_menu, accept: comma, send: Page_Up }`。
4. **`speller`** 拼寫處理器，接受字符按鍵，編輯輸入

   配置示例：
   ```yaml
   speller:
     alphabet: zyxwvutsrqponmlkjihgfedcbaZYXWVUTSRQPONMLKJIHGFEDCBA`
     initials: zyxwvutsrqponmlkjihgfedcbaZYXWVUTSRQPONMLKJIHGFEDCBA
     delimiter: " '"  # 空格作为拼音分隔符；' 可手动分割拼音
     algebra:
       # 模糊音：zh/ch/sh 派生出 z/c/s
       # - derive/^([zcs])h/$1/
       # 超级简拼：只打声母即可出词
       - abbrev/^([a-z]).+$/$1/
       - abbrev/^([zcs]h).+$/$1/
       # v/u 互转：支持 qv → qu / nve → nue
       - derive/^([nl])ve$/$1ue/
       - derive/^([jqxy])u/$1v/
       # 自动纠错：手误按键顺序
       - derive/([zcs])h(a|e|i|u|ai|ei|an|en|ou|uo|ua|un|ui|uan|uai|uang|ang|eng|ong)$/h$1$2/  # hzi → zhi
       - derive/^([wghk])ai$/$1ia/  # wia → wai
   ```

   效果演示：
   - `alphabet` 定义可用按键：不在其中的按键不进入拼写，可能被其他处理器直接上屏。
   - `initials` 定义仅作为始码的按键：`` ` `` 排除在 initials 外，所以单独输入 `` ` `` 可直接上屏（用于辅码引导）。
   - `delimiter: " '"`：输入 `zhong'guo` 与 `zhong guo` 等效，都识别为两个字。
   - `abbrev` 超级简拼：输入 `zg` 匹配到 `zhongguo`，出现"中国"等词。
   - `derive` 模糊音：取消注释 `derive/^([zcs])h/$1/` 后，输入 `zong` 也能匹配 `zhong` 的字词（卷舌音模糊）。
   - 自动纠错：输入 `hzi` 被纠正为 `zhi`；输入 `wia` 被纠正为 `wai`。
5. **`punctuator`** 句讀處理器，將單個字符按鍵直接映射爲標點符號或文字

   配置示例：
   ```yaml
   punctuator:
     __include: default:/punctuator     # 从 default.yaml 导入通用配置
     digit_separators: ",.:"            # 数字分隔符：在数字后输入这些字符不触发标点
     full_shape:
       ',' : { commit: ， }             # 单映射：逗号直接上屏全角逗号
       '.' : { commit: 。 }
       '/' : [ ／, ÷ ]                  # 候选映射：可选 / 或 ÷
       '''': { pair: [ '‘', '’' ] }     # 成对映射：输入光标插入配对符号
       '"' : { pair: [ '“', '”' ] }
       '<' : [ 《, 〈, «, ‹ ]           # 多候选：循环切换
     half_shape:
       ',' : '，'                       # 半角模式下仍输出全角中文标点
       '.' : '。'
       '/' : '/'                        # 斜杠保持半角
   ```

   效果演示：
   - 全角模式按 `,`：直接上屏 `，`。
   - 全角模式按 `/`：出现候选 `1.／ 2.÷`，可用数字键选择。
   - 全角模式按 `'`：光标两侧插入 `‘’`，光标位于中间（pair 配对）。
   - 全角模式按 `<`：出现候选 `1.《 2.〈 3.« 4.‹`，支持循环切换。
   - `digit_separators: ",.:"`：输入 `3.14` 时，`.` 不会触发标点，而是作为数字的一部分。双击 `.` 则恢复标点映射。
   - 切换半角模式（按 Control+Shift+3）：英文标点恢复半角，但中文标点仍输出全角。
6. `selector` 選字處理器，處理數字選字鍵〔可以換成別的哦〕、上、下候選定位、換頁

   配置示例：
   ```yaml
   selector:
     bindings:
       Up: previous_candidate     # ↑: 上一个候选项
       Down: next_candidate       # ↓: 下一个候选项
       Prior: previous_page       # PageUp: 上一页
       Next: next_page            # PageDown: 下一页
   ```

   效果演示：
   - 候选窗出现"1.中 2.种 3.重 4.钟 5.终"，按 `3` 上屏"重"。
   - 按 `↓` 键：高亮下移到"种"。
   - 按 `PageDown`：翻到下一页候选 `6.忠 7.肿 ...`。
   - 可在 `menu` 中修改备选标签或按键 `alternative_select_keys: ASDFGHJKL`，则用 A~L 选字。
7. `navigator` 處理輸入欄內的光標移動

   配置示例：
   ```yaml
   navigator:
     bindings:
       Left: left_by_char_no_loop         # ←: 按字符左移（不循环）
       Right: right_by_char_no_loop       # →: 按字符右移（不循环）
       Shift+Left: left_by_syllable       # Shift+←: 按音节左跳
       Shift+Right: right_by_syllable     # Shift+→: 按音节右跳
       Home: home                         # Home: 跳到首
       End: end                           # End: 跳到尾
   ```

   效果演示：
   - 输入 `zhongguoren`，按 `←`：光标在 `n` 前逐字符左移。
   - 输入 `zhongguoren`，按 `Shift+←`：光标从 `ren` 跳到 `guo` 前（按音节跳转）。
   - `no_loop` 表示移动到边界时停止，不加 `no_loop` 则循环跳到另一端。
8. `express_editor` 編輯器，處理空格、回車上屏、回退鍵

   配置示例：
   ```yaml
   editor:
     bindings:
       space: confirm                        # 空格：上屏首选候选项
       Return: commit_raw_input              # 回车：上屏原始输入码
       Control+Return: commit_script_text    # Ctrl+回车：上屏变换后文字
       Control+Shift+Return: commit_comment  # Ctrl+Shift+回车：上屏注释
       BackSpace: revert                     # 退格：撤销上次输入
       Delete: delete                        # Delete：向后删除
       Control+BackSpace: back_syllable      # Ctrl+退格：删除一个音节
       Control+Delete: delete_candidate      # Ctrl+Delete：删除/降权候选项
       Escape: cancel                        # Esc：取消全部输入
   ```

   效果演示：
   - 输入 `nihao`，按 `空格`：上屏"你好"。
   - 输入 `nihao`，按 `回车`：直接上屏原始编码 `nihao`（可用于临时输入英文）。
   - 输入 `zhongguo`，按 `Ctrl+回车`：上屏经 `preedit_format` 转换后的文本。
   - 输入 `nihao`，按 `BackSpace`：回退到 `niha`。
   - 输入 `zhongguoren`，按 `Ctrl+BackSpace`：整音节删除 `ren`。
   - 按 `Esc`：清空所有未上屏输入。
9. *`fluid_editor`* 句式編輯器，用於以空格斷詞、回車上屏的【注音】、【語句流】等輸入方案，替換`express_editor`

   配置示例：
   ```yaml
   engine:
     processors:
       # - express_editor    # 注释掉
       - fluid_editor        # 替换为 fluid_editor
   ```

   效果演示：
   - 与 `express_editor` 的区别：`fluid_editor` 中空格键分段而非上屏，回车键才上屏整句。
   - 适用于注音（注音符号输入）等以空格断词的连续输入方案。
10. *`chord_composer`* 和絃作曲家或曰並擊處理器，用於【宮保拼音】等多鍵並擊的輸入方案

   配置示例：
   ```yaml
   engine:
     processors:
       # - speller          # 注释掉常规拼写
       - chord_composer     # 使用并击处理
   ```

   效果演示：
   - 同时按下多个键（如左手按声母、右手按韵母），同时释放后输出一个字。
   - 不同于拼音逐个按键，并击方案一次同时按键即出字，用于速录场景。
11. `lua_processor` 使用`lua`自定義按鍵，後接`@`+`lua`函數名
    - `lua`函數名即用戶文件夾內`rime.lua`中函數名，參數爲`(key, env)`

   配置示例：
   ```yaml
   engine:
     processors:
       - lua_processor@*select_character  # 以词定字功能

   # 配合 key_binder 使用
   key_binder:
     select_first_character: "bracketleft"   # [ 上屏首字
     select_last_character: "bracketright"   # ] 上屏末字
   ```

   效果演示：
   - 输入 `zhongguo` 出现候选"中国"，按 `[`：上屏"中"（首字），按 `]`：上屏"国"（末字）。
   - `lua` 函数在 `rime.lua` 中定义，函数名前的 `*` 表示模块级函数。
   - `key_binder` 中需配置对应的按键触发。

### 二、`segmentors`



- 這批組件識別不同內容類型，將輸入碼分段並加上`tag`

1. `ascii_segmentor` 標識西文段落〔譬如在西文模式下〕字母直接上屛

   效果演示：
   - 在中文模式输入 `hello`：被 `abc_segmentor` 标为 `abc` tag，进入拼音翻译。
   - 切换到英文模式后输入 `hello`：被 `ascii_segmentor` 标为西文段落，字母直接上屏，不走翻译器。
2. `matcher` 配合`recognizer`標識符合特定規則的段落，如網址、反查等，加上特定`tag`

   效果演示：
   - 输入 `https://example.com`：`recognizer` 中 `url` 规则匹配到该输入，`matcher` 给这段输入加上特定 tag，使后续 `translator` 可按 tag 匹配处理。
   - 输入 `U4e2d`：`recognizer` 中 `unicode` 规则匹配，`matcher` 加上对应 tag，`lua_translator@*unicode` 根据 tag 翻译并输出字符"中"。
   - `recognizer` 定义匹配模式，`matcher` 负责执行分段和加 tag。
3. **`abc_segmentor`** 標識常規的文字段落，加上`abc`這個`tag`

   效果演示：
   - 输入拼音 `nihao`：被标为 `abc` tag，随后 `script_translator` 根据 `abc` tag 翻译成"你好"。
   - 输入双拼编码 `nk`（自然码双拼的 `nihao`）：同样标为 `abc` tag。
   - 这是最核心的分段器，常规输入都经过它标记为 `abc` tag。
4. `punct_segmentor` 標識句讀段落〔鍵入標點符號用〕加上`punct`這個`tag`

   效果演示：
   - 输入 `v1`（触发了 recognizer 的 punct 规则）：被标为 `punct` tag。
   - 随后 `punct_translator` 只处理带 `punct` tag 的段落，将 `v1` 翻译为对应符号。
   - 普通标点键（如 `,`）直接由 `punctuator` processor 处理上屏，不经过翻译器。
5. `fallback_segmentor` 標識其他未標識段落

   效果演示：
   - 如果有任何输入未被前面的 segmentors 标记，`fallback_segmentor` 会兜底标记。
   - 确保所有输入都能进入翻译流程，防止输入静默丢失。
6. **`affix_segmentor`** 用戶自定義`tag`
   - 此項可加載多個實例，後接`@`+`tag`名

   配置示例：
   ```yaml
   engine:
     segmentors:
       - affix_segmentor@radical_lookup  # 自定义 radical_lookup tag

   radical_lookup:
     tag: radical_lookup
     prefix: "uU"  # 触发前缀
     dictionary: radical_pinyin
   ```

   效果演示：
   - 输入 `uUzhong`：`affix_segmentor@radical_lookup` 识别前缀 `uU`，将这段输入标记为 `radical_lookup` tag。
   - 后续 `table_translator@radical_lookup` 只处理带 `radical_lookup` tag 的段落，用拆字词库翻译。
   - 可以创建多个 `affix_segmentor@xxx` 来支持不同的自定义前缀及 tag。
7. *`lua_segmentor`* 使用`lua`自定義切分，後接`@`+`lua`函數名

   配置示例：
   ```yaml
   engine:
     segmentors:
       - lua_segmentor@*my_custom_segmentor  # 自定义分段逻辑

   # rime.lua:
   # function my_custom_segmentor(input, env)
   #   -- 自定义分段逻辑
   # end
   ```

   效果演示：
   - 当内置 segmentors 无法满足需求时，用 Lua 编写自定义分段逻辑。
   - 例如：识别特定的编码前缀或特殊格式，给输入加上自定义 tag。

### 三、`translators`



- 這批組件翻譯特定類型的編碼段爲一組候選文字

1. `echo_translator` 沒有其他候選字時，回顯輸入碼〔輸入碼可以`Shift`+`Enter`上屛〕

   配置示例：
   ```yaml
   engine:
     translators:
       - echo_translator  # 通常放在 translator 列表末尾作为兜底
   ```

   效果演示：
   - 当输入编码在所有词典中都找不到匹配项时，`echo_translator` 将输入码本身作为候选显示。
   - 输入不存在的编码如 `xyz123`：候选区显示 `xyz123`，可用 Shift+Enter 上屏该编码。
   - 常用于反查或临时输入不便收录的词。
2. `punct_translator` 配合`punct_segmentor`轉換標點符號

   配置示例：
   ```yaml
   engine:
     translators:
       - punct_translator

   recognizer:
     patterns:
       punct: "^v([0-9]|10|[A-Za-z]+)$"  # 识别 v 模式
   ```

   效果演示：
   - 输入 `v1`，触发 `punct` 识别规则，`punct_translator` 将其翻译为对应的符号（如各种箭头、序号等）。
   - `punct_translator` 处理的是被标记为 `punct` tag 的编码段，与 `punctuator` processor（处理单个标点按键）是不同的组件。
3. **`table_translator`** 碼表翻譯器，用於倉頡、五筆等基於碼表的輸入方案

   配置示例：
   ```yaml
   engine:
     translators:
       - table_translator@custom_phrase  # 自定义短语
       - table_translator@melt_eng       # 英文词库
       - table_translator@cn_en          # 中英混合词库

   # 自定义短语翻译器配置
   custom_phrase:
     dictionary: ""            # 不挂载主词库
     user_dict: custom_phrase  # 挂载用户词库文件
     db_class: stabledb        # 只读数据库（stabledb）或可调频（tabledb）
     enable_completion: false  # 不补全
     enable_sentence: false    # 不组句
     initial_quality: 99       # 高权重，排在前面

   # 英文词库翻译器配置
   melt_eng:
     dictionary: melt_eng      # 挂载主词库
     enable_sentence: false    # 不组句
     enable_user_dict: false   # 禁用用户词典
     initial_quality: 1.1      # 权重低于拼音

   # 中英混合词翻译器
   cn_en:
     dictionary: ""            # 不挂载主词库
     user_dict: en_dicts/cn_en
     db_class: stabledb
     enable_completion: true   # 允许补全
     enable_sentence: false
     initial_quality: 0.5      # 低权重
   ```

   效果演示：
   - `table_translator` 从 `.dict.yaml` 文件中查编码→文字映射，返回精确匹配的候选项。
   - 输入 `custom_phrase.txt` 中的编码如 `d`：`table_translator@custom_phrase` 返回 `的`（`initial_quality: 99` 保证排在最前面）。
   - 输入 `hello`：`table_translator@melt_eng` 从英文词库中查找匹配，返回 `hello`（`initial_quality: 1.1`）。
   - 输入 `rug`：`table_translator@cn_en` 返回 `rug`（权重 0.5，排在拼音 `如果` 之后）。
   - `db_class: stabledb`：只读，不支持动态调频；`tabledb`：支持根据使用频率动态调整词频。
   - `enable_sentence: false`：不尝试组句，只查单条记录。
   - 仓颉/五笔方案使用 `table_translator` 作为主翻译器，查码表输出汉字。
4. @
5. cangjie
6. wubi
7. **`script_translator`** 腳本翻譯器，用於拼音、粵拼等基於音節表的輸入方案

   配置示例：
   ```yaml
   engine:
     translators:
       - script_translator  # 主翻译器，处理带 abc tag 的段落

   translator:
     dictionary: rime_ice              # 挂载词库
     enable_word_completion: true      # 大于4音节的词条自动补全
     spelling_hints: 8                 # 显示拼音提示
     always_show_comments: true        # 强制显示注释
     initial_quality: 1.2              # 拼音权重高于英文
     comment_format:                   # 用符号包裹注释
       - xform/^/［/
       - xform/$/］/
     preedit_format:                   # 影响输入框显示和Shift+回车
       - xform/([jqxy])v/$1u/          # 显示 ju qu xu yu
       - xform/([nl])v/$1v/            # 显示 nv lv
   ```

   效果演示：
   - 输入 `zhongguo`：`script_translator` 通过 `algebra` 拼写规则将编码拆分为 `zhong` + `guo`，从词库查找匹配，返回"中国"等候选。
   - `enable_word_completion: true`：输入 `zhongguorenmin` 超过4音节时，自动尝试补全匹配。
   - `initial_quality: 1.2`：拼音候选的权重1.2，高于英文的1.1，确保拼音候选排在英文前面。
   - `preedit_format`：输入框显示 `ju qu xu yu` 而不是 `jv qv xv yv`，但点击 Shift+Enter 上屏变换后文本。
   - `comment_format`：在拼音注释外包裹 [`［` `］`，供 `corrector.lua` 识别判断。
   - 与 `table_translator` 区别：`script_translator` 可使用 `algebra` 拼写运算（模糊音、纠错等），`table_translator` 则直接查码表。

8. @
9. pinyin
10. jyutping
11. *`reverse_lookup_translator`* 反查翻譯器，用另一種編碼方案查碼

   效果演示：
   - 在拼音方案中用仓颉码反查：输入仓颉编码，翻译器用仓颉方案查出对应汉字。
   - Rime 1.0 后推荐使用 `reverse_lookup_filter` 代替此翻译器，更灵活。
12. *`history_translator`* 產生commit歷史候選
    - tag: 同 Translator 說明
    - initial_quality: 同 Translator 說明
    - size: 設定候選記錄量，預設: 0 等同(commit_record最大儲存量 20）
    - input: 觸發此翻譯器的字串

   配置示例：
   ```yaml
   engine:
     translators:
       - history_translator

   history_translator:
     input: ""         # 空字符串表示所有输入都触发
     size: 10          # 显示最近 10 条输入历史
     initial_quality: 0.8  # 权重低于普通翻译
   ```

   效果演示：
   - 输入任何编码时，之前上屏过的内容会作为候选出现在列表中。
   - 类似"最近使用"功能，方便重复输入相同内容。
   - `input: ""`（空）对所有输入生效；设置 `input: "rq"` 则仅输入 `rq` 时触发。
13. **`lua_translator`** 使用`lua`自定義輸入，例如動態輸入當前日期、時間，後接`@`+`lua`函數名
    - `lua`函數名即用戶文件夾內`rime.lua`中函數名，參數爲`(input, seg, env)`
    - 可以`env.engine.context:get_option("option_name")`方式綁定到`switch`開關／`key_binder`快捷鍵

   配置示例：
   ```yaml
   engine:
     translators:
       - lua_translator@*date_translator     # 日期时间
       - lua_translator@*lunar               # 农历
       - lua_translator@*uuid                # UUID
       - lua_translator@*unicode             # Unicode 字符
       - lua_translator@*number_translator   # 数字金额大写
       - lua_translator@*calc_translator     # 计算器

   date_translator:
     date: rq       # 输入 rq → 2022-11-29
     time: sj       # 输入 sj → 18:13
     week: xq       # 输入 xq → 星期二
     datetime: dt   # 输入 dt → ISO 8601 格式
     timestamp: ts  # 输入 ts → 时间戳

   lunar: nl         # 输入 nl → 农历
   uuid: uuid        # 输入 uuid → 随机 UUID
   ```

   效果演示：
   - 输入 `rq`：`lua_translator@*date_translator` 动态生成当前日期 `2026-06-30`。
   - 输入 `sj`：输出当前时间 `14:25`。
   - 输入 `nl`：`lua_translator@*lunar` 输出农历日期。
   - 输入 `uuid`：`lua_translator@*uuid` 生成一个 UUID。
   - 输入 `U4e2d`：`lua_translator@*unicode` 输出 Unicode 字符"中"。
   - 输入 `R1234.56`：`lua_translator@*number_translator` 输出"一千二百三十四元五角六分"。
   - 输入 `cC1+2-3*4`：`lua_translator@*calc_translator` 输出计算结果。
   - 触发需配合 `recognizer/patterns` 定义输入规则。

### 四、`filters`



- 這批組件過濾翻譯的結果，自定義濾鏡皆可使用開關調控

1. `uniquifier` 過濾重複的候選字，有可能來自**`simplifier`**

   配置示例：
   ```yaml
   engine:
     filters:
       # ... other filters ...
       - uniquifier  # 放在 filter 列表最后
   ```

   效果演示：
   - `simplifier@emoji` 可能将"笑"同时展开为"笑"和"😊"（如果两者文字相同），`uniquifier` 消除重复项。
   - 多个 translator 可能产生相同候选（如拼音和英文都返回 `hello`），`uniquifier` 去重只保留一个。
   - 建议始终放在 filters 列表的最后。
2. `cjk_minifier` 字符集過濾〔僅用於`script_translator`，使之支援`extended_charset`開關〕

   配置示例：
   ```yaml
   engine:
     filters:
       - cjk_minifier

   switches:
     - name: extended_charset
       states: [ 常用, 扩展 ]  # 开关控制字符集范围
   ```

   效果演示：
   - 配合 `switches` 中的 `extended_charset` 开关使用。
   - 开关在"常用"状态时，过滤掉扩展字符集的生僻字，只保留常用字。
   - 开关切换到"扩展"时，允许显示全部字符（包括生僻字），如大字表 `41448` 的字。
3. **`single_char_filter`** 單字過濾器，如加載此組件，則屛敝詞典中的詞組〔僅`table_translator`有效〕

   配置示例：
   ```yaml
   engine:
     filters:
       - single_char_filter  # 过滤词组，只留单字
   ```

   效果演示：
   - 启用后，码表翻译器（如仓颉、五笔）返回的候选列表中，词组被过滤掉，仅保留单字候选。
   - 输入仓颉编码 `obo`（火月人）：原应返回"侦侦伺側……"，启用后只返回单字"侦"。
   - 对 `script_translator`（拼音）无效。
4. **`simplifier`** 用字轉換

   配置示例：
   ```yaml
   engine:
     filters:
       - simplifier@emoji                        # Emoji 转换
       - simplifier@traditionalize               # 简繁转换

   # Emoji 转换配置
   emoji:
     option_name: emoji           # 对应 switches 中的开关名
     opencc_config: emoji.json    # OpenCC 映射配置文件
     inherit_comment: false       # 不继承原词的注释

   # 简繁转换配置
   traditionalize:
     option_name: traditionalization  # 对应 switches 中的开关名
     opencc_config: s2t.json         # 简体→繁体 OpenCC 配置
     tips: none                      # 不显示转换提示
     tags: [ abc, number, gregorian_to_lunar ]  # 只在指定 tag 生效
   ```

   效果演示：
   - `simplifier@emoji`：输入 `xiaolian` 出现"笑脸"，同时通过 OpenCC 映射自动追加候选"😊"。开关 `emoji` 控制是否启用。
   - `simplifier@traditionalize`：输入 `zhong` 出现"中"，开关打开后同时追加"中"的繁体形式（虽然"中"简繁相同；换成"国"→"國"更明显）。
   - `option_name` 绑定 `switches` 中的同名开关，用户可通过快捷键切换。
   - `tags` 限制：`traditionalize` 只在 `abc`、`number`、`gregorian_to_lunar` tag 生效，不对反查等其他 tag 做简繁转换。
   - OpenCC 配置可选 `s2t.json`（简体到繁体）、`s2hk.json`（到香港繁体）、`s2tw.json`（到台湾正体）、`s2twp.json`（到台湾正体+词汇）。
5. **`reverse_lookup_filter`** 反查濾鏡，以更靈活的方式反查，Rime1.0後替代*`reverse_lookup_translator`*
   - 此項可加載多個實例，後接`@`+濾鏡名〔如：`pinyin_lookup`、`jyutping_lookup`等〕

   配置示例：
   ```yaml
   engine:
     filters:
       - reverse_lookup_filter@radical_reverse_lookup  # 部件拆字反查滤镜

   radical_reverse_lookup:
     tags: [ radical_lookup ]   # 只处理带 radical_lookup tag 的段落
     dictionary: rime_ice       # 拼音标注来源（显示注音）
     # comment_format:          # 自定义注释格式
     #   - xform/^/(/
     #   - xform/$/)/
   ```

   效果演示：
   - 输入 `uUzhong` 触发拆字反查：返回"中"(由 `table_translator@radical_lookup` 翻译)。
   - `reverse_lookup_filter@radical_reverse_lookup` 为返回的"中"追加拼音注释 `zhōng`（来自 `rime_ice` 词典）。
   - 候选项显示为：`1.中 [zhōng]`。
   - `tags: [ radical_lookup ]` 确保只在拆字反查时添加拼音注释，不影响普通拼音输入。
6. **`lua_filter`** 使用`lua`自定義過濾，例如過濾字符集、調整排序，後接`@`+`lua`函數名
   - `lua`函數名即用戶文件夾內`rime.lua`中函數名，參數爲`(input, env)`
   - 可以`env.engine.context:get_option("option_name")`方式綁定到`switch`開關／`key_binder`快捷鍵

   配置示例：
   ```yaml
   engine:
     filters:
       - lua_filter@*corrector               # 错音错字提示
       - lua_filter@*autocap_filter          # 英文自动大写
       - lua_filter@*v_filter                # v 模式 symbols 优先
       - lua_filter@*pin_cand_filter         # 置顶候选项
       - lua_filter@*long_word_filter        # 长词优先
       - lua_filter@*reduce_english_filter   # 降低部分英文词权重

   # 错音错字提示 filter，校验编码与拼音的匹配
   # （corrector 没有额外的配置项，由 translator 的 spelling_hints
   #   和 comment_format 配合工作）

   # 置顶候选项
   pin_cand_filter:
     # 格式：编码<Tab>字词1<Space>字词2……
     - d	的
     - m	吗 嘛
     - hm	后面

   # 长词优先：将 count 个长词插入到第 idx 个位置
   long_word_filter:
     count: 2
     idx: 4

   # 降低英文词权重
   reduce_english_filter:
     mode: custom       # all | custom | none
     idx: 2             # 降低到第 idx 个位置
     words: [ aid, ann, bail, bait, ... ]
   ```

   效果演示：
   - **`corrector`**（错音错字提示）：输入 `zong`（应为 `zhong`）选"中"时，注释提示 `zhong`（正确的拼音），帮助用户纠正错音。
   - **`autocap_filter`**（英文自动大写）：在句首或特定位置，自动将英文单词首字母大写。
   - **`v_filter`**（v 模式优先）：确保 `v` 模式下的 symbols 输入优先被处理。
   - **`pin_cand_filter`**（置顶候选项）：输入 `d` 时，"的"始终被置顶为第1候选。输入 `m` 时，"吗 嘛"被置顶（覆盖 custom_phrase.txt 中的 `呒` `呣`）。
   - **`long_word_filter`**（长词优先）：设置 `count: 2, idx: 4`，输入 `jie` 得到 `1.接 2.解 3.姐 4.饥饿 5.极恶 6.结 7.界……`，两个长词被提升到第4、5位。
   - **`reduce_english_filter`**（降低英文词）：输入 `rug`，原候选为 `1.rug 2.如果……`，降低后变为 `1.如果 2.rug……`。
     - `mode: all`：降低所有内置规则匹配的短单词（3~4位，前2~3位是完整拼音、最后一位是声母）。
     - `mode: custom`：只降低 `words` 列表中指定的单词。
     - `mode: none`：不降低任何单词。