-- Automation LAP — Experiment A smoke-test exporter
--
-- This file is loaded by an Automation exporter DLL through the official
-- Exporter SDK. Automation calls the global DoExport(CarCalculator, CarFile)
-- function and writes the returned Files table to the export destination.
--
-- Scope: metadata only. Physical vehicle data is deliberately excluded until
-- this smoke test has been validated on the installed Automation version.

local SCHEMA_VERSION = "0.1.0"
local EXPORTER_VERSION = "0.1.0-smoke"
local OUTPUT_FILENAME = "automation-lap-vehicle.json"

local JSON_NULL = {}

local function json_array(values)
    return {
        __json_kind = "array",
        values = values or {},
    }
end

local function escape_json_string(value)
    local escaped = value
        :gsub("\\", "\\\\")
        :gsub('"', '\\"')
        :gsub("\b", "\\b")
        :gsub("\f", "\\f")
        :gsub("\n", "\\n")
        :gsub("\r", "\\r")
        :gsub("\t", "\\t")

    escaped = escaped:gsub("[%z\1-\31]", function(character)
        return string.format("\\u%04x", string.byte(character))
    end)

    return '"' .. escaped .. '"'
end

local function sorted_keys(value)
    local keys = {}

    for key, _ in pairs(value) do
        if key ~= "__json_kind" and key ~= "values" then
            keys[#keys + 1] = key
        end
    end

    table.sort(keys, function(left, right)
        return tostring(left) < tostring(right)
    end)

    return keys
end

local function encode_json(value)
    if value == JSON_NULL then
        return "null"
    end

    local value_type = type(value)

    if value_type == "string" then
        return escape_json_string(value)
    end

    if value_type == "number" then
        if value ~= value or value == math.huge or value == -math.huge then
            error("Cannot encode a non-finite number as JSON")
        end

        return tostring(value)
    end

    if value_type == "boolean" then
        return value and "true" or "false"
    end

    if value_type ~= "table" then
        error("Unsupported JSON value type: " .. value_type)
    end

    if value.__json_kind == "array" then
        local encoded_items = {}

        for index, item in ipairs(value.values) do
            encoded_items[index] = encode_json(item)
        end

        return "[" .. table.concat(encoded_items, ",") .. "]"
    end

    local encoded_members = {}

    for _, key in ipairs(sorted_keys(value)) do
        encoded_members[#encoded_members + 1] =
            escape_json_string(tostring(key)) .. ":" .. encode_json(value[key])
    end

    return "{" .. table.concat(encoded_members, ",") .. "}"
end

local function safe_index(value, key)
    if value == nil then
        return nil
    end

    local ok, result = pcall(function()
        return value[key]
    end)

    if ok then
        return result
    end

    return nil
end

local function read_path(root, path)
    local current = root

    for segment in string.gmatch(path, "[^.]+") do
        current = safe_index(current, segment)

        if current == nil then
            return nil
        end
    end

    return current
end

local function normalize_text(value)
    if value == nil then
        return nil
    end

    local value_type = type(value)

    if value_type == "string" then
        if value == "" then
            return nil
        end

        return value
    end

    if value_type == "number" or value_type == "boolean" then
        return tostring(value)
    end

    local nested_name = safe_index(value, "Name")

    if type(nested_name) == "string" and nested_name ~= "" then
        return nested_name
    end

    return nil
end

local function read_first_text(root, candidate_paths)
    for _, path in ipairs(candidate_paths) do
        local value = normalize_text(read_path(root, path))

        if value ~= nil then
            return value, path
        end
    end

    return nil, nil
end

local function utc_timestamp()
    local ok, result = pcall(function()
        return os.date("!%Y-%m-%dT%H:%M:%SZ")
    end)

    if ok and type(result) == "string" then
        return result
    end

    return nil
end

local function value_or_null(value)
    if value == nil then
        return JSON_NULL
    end

    return value
end

function DoExport(CarCalculator, CarFile)
    local diagnostics = {}

    local model_name, model_path = read_first_text(CarCalculator, {
        "CarInfo.ModelName",
        "CarInfo.PlatformInfo.ModelName",
        "CarInfo.PlatformInfo.Name",
        "CarInfo.Name",
        "ModelName",
    })

    local trim_name, trim_path = read_first_text(CarCalculator, {
        "CarInfo.TrimInfo.Name",
        "CarInfo.TrimName",
        "TrimName",
    })

    local automation_version, automation_version_path = read_first_text(CarCalculator, {
        "AutomationVersion",
        "GameVersion",
        "CarInfo.AutomationVersion",
        "CarInfo.GameVersion",
    })

    local exported_at_utc = utc_timestamp()

    if model_name == nil then
        diagnostics[#diagnostics + 1] = "model_name_not_found"
    end

    if trim_name == nil then
        diagnostics[#diagnostics + 1] = "trim_name_not_found"
    end

    if automation_version == nil then
        diagnostics[#diagnostics + 1] = "automation_version_not_exposed"
    end

    if exported_at_utc == nil then
        diagnostics[#diagnostics + 1] = "utc_clock_not_available"
    end

    local document = {
        diagnostics = json_array(diagnostics),
        exportedAtUtc = value_or_null(exported_at_utc),
        exporterVersion = EXPORTER_VERSION,
        schemaVersion = SCHEMA_VERSION,
        source = {
            automationVersion = value_or_null(automation_version),
            automationVersionPath = value_or_null(automation_version_path),
            kind = "Automation",
        },
        vehicle = {
            modelName = value_or_null(model_name),
            modelNamePath = value_or_null(model_path),
            trimName = value_or_null(trim_name),
            trimNamePath = value_or_null(trim_path),
        },
    }

    local files = {
        [OUTPUT_FILENAME] = encode_json(document) .. "\n",
    }

    -- Only scalar values are included here because the C++ bridge receives the
    -- Data table through AddLuaFloatData/AddLuaStringData.
    local data = {
        exporterVersion = EXPORTER_VERSION,
        schemaVersion = SCHEMA_VERSION,
        smokeTestOutputFilename = OUTPUT_FILENAME,
    }

    return files, data
end
