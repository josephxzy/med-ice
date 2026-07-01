-- 医学检索模式（mEd 前缀触发）
-- 输入 mEd + 简拼 → 仅检索医学词库
-- 如 mEdaben → 匹配所有以 aben 开头的简拼（阿苯、阿苯达唑…）

local M = {}
local prefix_map = {}
local loaded = false

local function load_index(env)
    if loaded then return end
    local path = env.engine.schema.user_data_dir .. "/med_abbrev_index.txt"
    local file = io.open(path, "r")
    if not file then
        loaded = true
        return
    end

    for line in file:lines() do
        local abbrev, _, text = line:match("^(%S+)\t(%S+)\t(.+)$")
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
end

function M.func(input, seg, env)
    load_index(env)

    if #input < 2 then return 2 end

    -- input 是去掉 mEd 前缀后的简拼编码
    local prefix = input:sub(1, 2)
    local list = prefix_map[prefix]
    if not list then return 2 end

    local count = 0
    for _, c in ipairs(list) do
        if c.abbrev:sub(1, #input) == input then
            local cand = Candidate("med", seg.start, seg._end, c.text, "")
            cand.quality = 100
            yield(cand)
            count = count + 1
            if count >= 10 then break end
        end
    end

    return 1
end

return M
