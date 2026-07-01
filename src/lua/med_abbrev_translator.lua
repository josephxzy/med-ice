-- 医学超级简拼
-- 输入首字母简拼（如 ftlm）→ 匹配医学长词（如 酚妥拉明）
-- 至多返回 4 个候选

local M = {}

-- 从文件加载索引：{ ["ft"] = {{abbrev="ftlm", text="酚妥拉明"}, ...}, ... }
local prefix_map = {}
local loaded = false

-- 加载简拼索引文件
local function load_index(env)
    if loaded then return end
    local path = env.engine.schema.user_data_dir .. "/med_abbrev_index.txt"
    local file = io.open(path, "r")
    if not file then
        loaded = true
        return
    end

    for line in file:lines() do
        local abbrev, _, text = line:match("^(%S+)%s+(%S+)%s+(.+)$")
        if abbrev and text and #abbrev >= 2 then
            local prefix = abbrev:sub(1, 2)
            if not prefix_map[prefix] then
                prefix_map[prefix] = {}
            end
            table.insert(prefix_map[prefix], { abbrev = abbrev, text = text })
        end
    end
    file:close()
    loaded = true
end

function M.init(env)
    M.index_built = false
end

function M.func(input, seg, env)
    -- 仅处理 2-10 个纯小写字母的简拼输入
    if #input < 2 or #input > 10 then return 2 end
    if not input:match("^[a-z]+$") then return 2 end

    -- 延迟加载索引
    load_index(env)

    -- 按输入的前 2 字母查找
    local prefix = input:sub(1, 2)
    local list = prefix_map[prefix]
    if not list then return 2 end

    local count = 0
    for _, c in ipairs(list) do
        -- 前缀匹配：输入的简拼是候选简拼的前缀
        if c.abbrev:sub(1, #input) == input then
            local cand = Candidate("med_abbrev", seg.start, seg._end, c.text, "")
            cand.quality = 70
            yield(cand)
            count = count + 1
            if count >= 4 then break end
        end
    end

    return 1
end

return M
