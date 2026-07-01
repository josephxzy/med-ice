-- 医学检索模式（mEd 前缀触发）
-- 输入 mEd + 简拼/全拼 → 仅检索医学词库

local M = {}
local prefix_map = {}
local loaded = false

local function build_index(env)
    if loaded then return end
    local path = env.engine.schema.user_data_dir .. "/med_abbrev_index.txt"
    local file = io.open(path, "r")
    if not file then
        loaded = true
        return
    end

    for line in file:lines() do
        local abbrev, code, text = line:match("^(%S+)\t(%S+)\t(.+)$")
        if abbrev and code and text and #abbrev >= 2 then
            local entry = { abbrev = abbrev, code = code:gsub(" ", ""), text = text }
            -- 双索引：简拼前缀 + 全拼前缀
            local keys = {}
            keys[abbrev:sub(1, 2)] = true
            if entry.code:sub(1, 2) ~= abbrev:sub(1, 2) then
                keys[entry.code:sub(1, 2)] = true
            end
            for k, _ in pairs(keys) do
                if not prefix_map[k] then prefix_map[k] = {} end
                table.insert(prefix_map[k], entry)
            end
        end
    end
    file:close()
    loaded = true
end

function M.init(env)
    build_index(env)
end

function M.func(input, seg, env)
    if #input == 0 then
        local cand = Candidate("med", seg.start, seg._end, "〔输入简拼或全拼检索医学词库〕", "")
        cand.quality = 100
        yield(cand)
        return 1
    end

    if #input < 2 then return 2 end

    local key = input:sub(1, 2)
    local list = prefix_map[key]
    if not list then return 2 end

    local count = 0
    for _, c in ipairs(list) do
        if c.abbrev:sub(1, #input) == input or c.code:sub(1, #input) == input then
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
