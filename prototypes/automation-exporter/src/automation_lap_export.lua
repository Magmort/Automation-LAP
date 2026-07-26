-- Automation LAP — Experiment A smoke-test exporter
--
-- This file is loaded by an Automation exporter DLL through the official
-- Exporter SDK. Automation calls the global DoExport(CarCalculator, CarFile)
-- function and writes the returned Files table to the export destination.
--
-- Scope: metadata only. Physical vehicle data is deliberately excluded until
-- this smoke test has been validated on the installed Automation version.

local SCHEMA_VERSION = "0.1.1"
local INVENTORY_SCHEMA_VERSION = "0.1.0"
local EXPORTER_VERSION = "0.1.4-a3-final-drive"
local OUTPUT_FILENAME = "automation-lap-vehicle.json"
local INVENTORY_OUTPUT_FILENAME = "automation-lap-field-inventory.json"
local EXPORT_TIMESTAMP_PLACEHOLDER = "__AUTOMATION_LAP_EXPORTED_AT_UTC__"

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
        if value ~= value or (math ~= nil and (value == math.huge or value == -math.huge)) then
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

    if type(value) ~= "table" then
        return nil
    end

    return value[key]
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

local function normalize_number(value)
    if type(value) == "number" then
        return value
    end

    return nil
end

local function read_first_number(root, candidate_paths)
    for _, path in ipairs(candidate_paths) do
        local value = normalize_number(read_path(root, path))

        if value ~= nil then
            return value, path
        end
    end

    return nil, nil
end

local function value_or_null(value)
    if value == nil then
        return JSON_NULL
    end

    return value
end

local function infer_kind(value)
    if value == nil then
        return "missing"
    end

    return type(value)
end

local function preview_value(value)
    local value_type = type(value)

    if value == nil then
        return JSON_NULL
    end

    if value_type == "number" or value_type == "string" or value_type == "boolean" then
        return value
    end

    if value_type == "table" then
        local name = normalize_text(value)

        if name ~= nil then
            return name
        end
    end

    return JSON_NULL
end

local function make_field(key, family, candidate_paths, unit_source, unit_internal, nature)
    local resolved_value = nil
    local resolved_path = nil

    for _, path in ipairs(candidate_paths) do
        local value = read_path(CarCalculatorGlobal, path)

        if value ~= nil then
            resolved_value = value
            resolved_path = path
            break
        end
    end

    local present = resolved_path ~= nil

    return {
        key = key,
        family = family,
        candidatePaths = json_array(candidate_paths),
        resolvedPath = value_or_null(resolved_path),
        present = present,
        luaType = infer_kind(resolved_value),
        valuePreview = preview_value(resolved_value),
        origin = "automation",
        presence = present and "observed" or "missing",
        nature = nature or "raw-choice",
        unitSource = unit_source or "unknown",
        unitInternalCandidate = unit_internal or "unknown",
        stability = "untested",
        redistribution = "unknown",
    }
end

local function make_function_probe(name, path)
    local value = read_path(CarCalculatorGlobal, path)
    local present = type(value) == "function"

    return {
        name = name,
        path = path,
        present = present,
        luaType = infer_kind(value),
        called = false,
        reason = "not_called_because_lua_protected_call_is_unavailable",
    }
end

local function build_inventory()
    local fields = {
        make_field("identity.modelName", "identity", { "CarInfo.PlatformInfo.Name", "CarInfo.ModelName", "ModelName" }, "text", "not-applicable", "raw-choice"),
        make_field("identity.trimName", "identity", { "CarInfo.TrimInfo.Name", "CarInfo.TrimName", "TrimName" }, "text", "not-applicable", "raw-choice"),
        make_field("source.lastAccessTime", "identity", { "lastAccessTime", "LastAccessTime" }, "seconds-or-runtime-native", "seconds", "raw-result"),
        make_field("source.automationVersion", "identity", { "AutomationVersion", "GameVersion", "CarInfo.AutomationVersion", "CarInfo.GameVersion", "CarInfo.PlatformInfo.GameVersion", "CarInfo.TrimInfo.GameVersion" }, "version", "not-applicable", "raw-result"),

        make_field("geometry.wheelBase", "geometry", { "CarInfo.PlatformInfo.WheelBase", "CarInfo.PlatformInfo.Body.WheelBase", "CarInfo.TrimInfo.Body.WheelBase", "CarParameters.length" }, "unknown", "m", "raw-result"),
        make_field("geometry.frontTrackWidth", "geometry", { "CarInfo.PlatformInfo.BaseFrontTrackWidth", "CarParameters.FrontTrackWidth", "CarInfo.PlatformInfo.Body.BaseFrontTrackWidth", "CarInfo.TrimInfo.Body.BaseFrontTrackWidth" }, "unknown", "m", "raw-result"),
        make_field("geometry.rearTrackWidth", "geometry", { "CarInfo.PlatformInfo.BaseRearTrackWidth", "CarParameters.RearTrackWidth", "CarInfo.PlatformInfo.Body.BaseRearTrackWidth", "CarInfo.TrimInfo.Body.BaseRearTrackWidth" }, "unknown", "m", "raw-result"),
        make_field("geometry.frontalArea", "geometry", { "CarInfo.PlatformInfo.FrontalArea", "CarInfo.PlatformInfo.Body.FrontalArea", "CarInfo.TrimInfo.Body.FrontalArea" }, "unknown", "m2", "raw-result"),
        make_field("geometry.bodyDimensions.x", "geometry", { "CarInfo.PlatformInfo.BodyDimensions.x", "CarInfo.PlatformInfo.Body.BodyDimensions.x", "CarInfo.TrimInfo.Body.BodyDimensions.x" }, "unknown", "m", "raw-result"),
        make_field("geometry.bodyDimensions.y", "geometry", { "CarInfo.PlatformInfo.BodyDimensions.y", "CarInfo.PlatformInfo.Body.BodyDimensions.y", "CarInfo.TrimInfo.Body.BodyDimensions.y" }, "unknown", "m", "raw-result"),
        make_field("geometry.bodyDimensions.z", "geometry", { "CarInfo.PlatformInfo.BodyDimensions.z", "CarInfo.PlatformInfo.Body.BodyDimensions.z", "CarInfo.TrimInfo.Body.BodyDimensions.z" }, "unknown", "m", "raw-result"),
        make_field("geometry.bodyType", "geometry", { "CarInfo.PlatformInfo.BodyType", "CarInfo.PlatformInfo.Body.BodyType", "CarInfo.TrimInfo.Body.BodyType" }, "text", "not-applicable", "raw-choice"),
        make_field("geometry.doors", "geometry", { "CarInfo.PlatformInfo.Doors", "CarInfo.PlatformInfo.Body.Doors", "CarInfo.TrimInfo.Body.Doors" }, "count", "count", "raw-result"),
        make_field("geometry.year", "geometry", { "CarInfo.PlatformInfo.Year", "CarInfo.PlatformInfo.Body.Year", "CarInfo.TrimInfo.Body.Year" }, "year", "year", "raw-result"),

        make_field("mass.total", "mass", { "CarInfo.TrimInfo.Results.Weight", "CarInfo.TrimInfo.Results.TotalWeight", "CarInfo.TrimInfo.Weight", "CarInfo.TrimInfo.Mass" }, "unknown", "kg", "raw-result"),
        make_field("mass.frontDistribution", "mass", { "CarInfo.TrimInfo.WeightDistributionFraction" }, "fraction", "fraction", "raw-result"),

        make_field("chassis.chassis", "chassis", { "CarInfo.PlatformInfo.Chassis" }, "text", "not-applicable", "raw-choice"),
        make_field("chassis.chassisMaterial", "chassis", { "CarInfo.PlatformInfo.ChassisMaterial" }, "text", "not-applicable", "raw-choice"),
        make_field("chassis.panelMaterial", "chassis", { "CarInfo.PlatformInfo.PanelMaterial" }, "text", "not-applicable", "raw-choice"),
        make_field("chassis.enginePlacement", "chassis", { "CarInfo.PlatformInfo.EnginePlacement" }, "text", "not-applicable", "raw-choice"),

        make_field("engine.familyName", "engine", { "EngineCalculator.EngineInfo.Family.Name", "CarInfo.TrimInfo.EngineInfo.Family.Name", "CarInfo.EngineInfo.Family.Name", "CarInfo.TrimInfo.EngineInfo.PlatformInfo.Name", "EngineCalculator.EngineInfo.PlatformInfo.Name" }, "text", "not-applicable", "raw-choice"),
        make_field("engine.variantName", "engine", { "EngineCalculator.EngineInfo.Variant.Name", "CarInfo.TrimInfo.EngineInfo.Name", "CarInfo.EngineInfo.Name", "CarInfo.TrimInfo.EngineInfo.ModelInfo.Name", "EngineCalculator.EngineInfo.ModelInfo.Name" }, "text", "not-applicable", "raw-choice"),
        make_field("engine.capacity", "engine", { "EngineCalculator.EngineInfo.Variant.Capacity", "CarInfo.TrimInfo.EngineInfo.Capacity", "CarInfo.EngineInfo.Capacity", "CarInfo.TrimInfo.EngineInfo.ModelInfo.Capacity", "CarInfo.TrimInfo.EngineInfo.PlatformInfo.Capacity", "EngineCalculator.EngineInfo.ModelInfo.Capacity", "EngineCalculator.EngineInfo.PlatformInfo.Capacity" }, "unknown", "m3", "raw-result"),
        make_field("engine.rpmLimit", "engine", { "EngineCalculator.EngineInfo.Variant.RPMLimit", "CarInfo.TrimInfo.EngineInfo.RPMLimit", "CarInfo.EngineInfo.RPMLimit", "CarInfo.TrimInfo.EngineInfo.ModelInfo.RPMLimit", "EngineCalculator.EngineInfo.ModelInfo.RPMLimit" }, "rpm", "rpm", "raw-result"),
        make_field("engine.fuelType", "engine", { "EngineCalculator.EngineInfo.Variant.FuelType", "CarInfo.TrimInfo.EngineInfo.FuelType", "CarInfo.EngineInfo.FuelType", "CarInfo.TrimInfo.EngineInfo.ModelInfo.Fuel.Name", "CarInfo.TrimInfo.EngineInfo.ModelInfo.Fuel.Type", "EngineCalculator.EngineInfo.ModelInfo.Fuel.Name", "EngineCalculator.EngineInfo.ModelInfo.Fuel.Type" }, "text", "not-applicable", "raw-choice"),

        make_field("transmission.driveType", "transmission", { "CarInfo.TrimInfo.DriveType", "CarInfo.TrimInfo.Gearbox.DriveType.Name", "CarInfo.TrimInfo.Gearbox.DriveType.ID", "CarParameters.DrivenWheels" }, "text", "not-applicable", "raw-choice"),
        make_field("transmission.gearboxType", "transmission", { "CarInfo.TrimInfo.GearboxType", "CarInfo.TrimInfo.Gearbox.Type.Name", "CarInfo.TrimInfo.Gearbox.Type.ID", "CarParameters.GearboxType" }, "text", "not-applicable", "raw-choice"),
        make_field("transmission.gearboxRatios", "transmission", { "CarInfo.TrimInfo.GearboxRatios", "CarParameters.GearboxRatios", "CarInfo.TrimInfo.Gearbox.Ratios" }, "text", "not-applicable", "raw-choice"),
        make_field("transmission.finalDrive", "transmission", { "CarInfo.TrimInfo.Gearbox.DiffRatio", "CarParameters.DiffRatio", "CarInfo.TrimInfo.AdvancedGearing.FinalDrive.Ratio" }, "ratio", "ratio", "raw-result"),
        make_field("transmission.differential", "transmission", { "CarInfo.TrimInfo.Differential", "CarInfo.TrimInfo.Gearbox.Differential.Name", "CarInfo.TrimInfo.Gearbox.Differential.ID", "CarParameters.CenterDiff" }, "text", "not-applicable", "raw-choice"),

        make_field("wheels.frontTyreWidth", "wheels", { "CarInfo.TrimInfo.FrontTyreWidth", "CarInfo.TrimInfo.TyreDetails.Front.Width" }, "unknown", "mm", "raw-result"),
        make_field("wheels.rearTyreWidth", "wheels", { "CarInfo.TrimInfo.RearTyreWidth", "CarInfo.TrimInfo.TyreDetails.Rear.Width" }, "unknown", "mm", "raw-result"),
        make_field("wheels.frontRimDiameter", "wheels", { "CarInfo.TrimInfo.FrontRimDiameter", "CarInfo.TrimInfo.TyreDetails.Front.Rim" }, "unknown", "inch", "raw-result"),
        make_field("wheels.rearRimDiameter", "wheels", { "CarInfo.TrimInfo.RearRimDiameter", "CarInfo.TrimInfo.TyreDetails.Rear.Rim" }, "unknown", "inch", "raw-result"),
        make_field("wheels.frontOverallDiameter", "wheels", { "CarInfo.TrimInfo.FrontOverallDiameter", "CarInfo.TrimInfo.TyreDetails.Front.OverallDiameter" }, "unknown", "mm", "raw-result"),
        make_field("wheels.rearOverallDiameter", "wheels", { "CarInfo.TrimInfo.RearOverallDiameter", "CarInfo.TrimInfo.TyreDetails.Rear.OverallDiameter" }, "unknown", "mm", "raw-result"),
        make_field("wheels.tyreType", "wheels", { "CarInfo.TrimInfo.TyreType", "CarInfo.TrimInfo.Tyres" }, "text", "not-applicable", "raw-choice"),

        make_field("brakes.frontBrakeForce", "brakes", { "CarInfo.TrimInfo.FrontBrakeForce", "CarInfo.TrimInfo.Brakes.Front.BrakeForce" }, "unknown", "N", "raw-result"),
        make_field("brakes.rearBrakeForce", "brakes", { "CarInfo.TrimInfo.RearBrakeForce", "CarInfo.TrimInfo.Brakes.Rear.BrakeForce" }, "unknown", "N", "raw-result"),
        make_field("brakes.frontBrakeType", "brakes", { "CarInfo.TrimInfo.FrontBrakeType", "CarInfo.TrimInfo.Brakes.Front.Discs.Name", "CarInfo.TrimInfo.Brakes.Front.Discs.DiscName" }, "text", "not-applicable", "raw-choice"),
        make_field("brakes.rearBrakeType", "brakes", { "CarInfo.TrimInfo.RearBrakeType", "CarInfo.TrimInfo.Brakes.Rear.Discs.Name", "CarInfo.TrimInfo.Brakes.Rear.Discs.DiscName" }, "text", "not-applicable", "raw-choice"),
        make_field("brakes.frontPadSize", "brakes", { "CarInfo.TrimInfo.FrontPadSize", "CarInfo.TrimInfo.Brakes.Front.PadType" }, "unknown", "dimensionless", "raw-result"),
        make_field("brakes.rearPadSize", "brakes", { "CarInfo.TrimInfo.RearPadSize", "CarInfo.TrimInfo.Brakes.Rear.PadType" }, "unknown", "dimensionless", "raw-result"),

        make_field("aerodynamics.activeWing", "aerodynamics", { "CarInfo.TrimInfo.ActiveWing" }, "text", "not-applicable", "raw-choice"),
        make_field("aerodynamics.activeCooling", "aerodynamics", { "CarInfo.TrimInfo.ActiveCooling" }, "text", "not-applicable", "raw-choice"),
        make_field("aerodynamics.undertray", "aerodynamics", { "CarInfo.TrimInfo.Undertray" }, "text", "not-applicable", "raw-choice"),
        make_field("aerodynamics.coolingAirflowFraction", "aerodynamics", { "CarInfo.TrimInfo.CoolingAirflowFraction" }, "fraction", "fraction", "raw-result"),
        make_field("aerodynamics.brakeCoolingFraction", "aerodynamics", { "CarInfo.TrimInfo.BrakeCoolingFraction" }, "fraction", "fraction", "raw-result"),

        make_field("suspension.frontType", "suspension", { "CarInfo.PlatformInfo.FrontSuspension" }, "text", "not-applicable", "raw-choice"),
        make_field("suspension.rearType", "suspension", { "CarInfo.PlatformInfo.RearSuspension" }, "text", "not-applicable", "raw-choice"),
        make_field("suspension.springs", "suspension", { "CarInfo.TrimInfo.Springs" }, "text", "not-applicable", "raw-choice"),
        make_field("suspension.dampers", "suspension", { "CarInfo.TrimInfo.Dampers" }, "text", "not-applicable", "raw-choice"),
        make_field("suspension.swayBars", "suspension", { "CarInfo.TrimInfo.SwayBars" }, "text", "not-applicable", "raw-choice"),
        make_field("suspension.frontSpringStiffness", "suspension", { "CarInfo.TrimInfo.FrontSpringStiffness", "CarInfo.TrimInfo.SuspensionDetails.Front.SpringStiffness" }, "unknown", "N/m", "raw-result"),
        make_field("suspension.rearSpringStiffness", "suspension", { "CarInfo.TrimInfo.RearSpringStiffness", "CarInfo.TrimInfo.SuspensionDetails.Rear.SpringStiffness" }, "unknown", "N/m", "raw-result"),
        make_field("suspension.frontDamperStiffness", "suspension", { "CarInfo.TrimInfo.FrontDamperStiffness", "CarInfo.TrimInfo.SuspensionDetails.Front.DamperStiffness" }, "unknown", "N*s/m", "raw-result"),
        make_field("suspension.rearDamperStiffness", "suspension", { "CarInfo.TrimInfo.RearDamperStiffness", "CarInfo.TrimInfo.SuspensionDetails.Rear.DamperStiffness" }, "unknown", "N*s/m", "raw-result"),
        make_field("suspension.frontSwayBarStiffness", "suspension", { "CarInfo.TrimInfo.FrontSwayBarStiffness", "CarInfo.TrimInfo.SuspensionDetails.Front.ARBStiffness" }, "unknown", "N/m", "raw-result"),
        make_field("suspension.rearSwayBarStiffness", "suspension", { "CarInfo.TrimInfo.RearSwayBarStiffness", "CarInfo.TrimInfo.SuspensionDetails.Rear.ARBStiffness" }, "unknown", "N/m", "raw-result"),
        make_field("suspension.rideHeight", "suspension", { "CarInfo.TrimInfo.RideHeight", "CarInfo.TrimInfo.SuspensionDetails.RideHeight" }, "unknown", "m", "raw-result"),
        make_field("suspension.frontCamber", "suspension", { "CarInfo.TrimInfo.FrontCamber", "CarInfo.TrimInfo.SuspensionDetails.Front.Camber" }, "unknown", "deg", "raw-result"),
        make_field("suspension.rearCamber", "suspension", { "CarInfo.TrimInfo.RearCamber", "CarInfo.TrimInfo.SuspensionDetails.Rear.Camber" }, "unknown", "deg", "raw-result"),
        make_field("suspension.frontToe", "suspension", { "CarInfo.TrimInfo.FrontToe", "CarInfo.TrimInfo.SuspensionDetails.Front.Toe" }, "unknown", "deg", "raw-result"),
        make_field("suspension.rearToe", "suspension", { "CarInfo.TrimInfo.RearToe", "CarInfo.TrimInfo.SuspensionDetails.Rear.Toe" }, "unknown", "deg", "raw-result"),

        make_field("performance.topSpeed", "performance", { "CarInfo.TrimInfo.Results.TopSpeed", "CarInfo.TrimInfo.TopSpeed" }, "unknown", "m/s", "raw-result"),
        make_field("performance.acceleration0To100", "performance", { "CarInfo.TrimInfo.Results.Acceleration0To100", "CarInfo.TrimInfo.Results.ZeroToOneHundred", "CarInfo.TrimInfo.Results.HundredTime" }, "unknown", "s", "raw-result"),
        make_field("performance.brakingDistance", "performance", { "CarInfo.TrimInfo.Results.BrakingDistance", "CarInfo.TrimInfo.Results.Braking100To0" }, "unknown", "m", "raw-result"),
    }

    local functions = {
        make_function_probe("GetCarParameters", "GetCarParameters"),
        make_function_probe("GetBrakingForces", "GetBrakingForces"),
        make_function_probe("CalculateDynamicCG", "CalculateDynamicCG"),
        make_function_probe("GetTotalEffectiveArea", "GetTotalEffectiveArea"),
        make_function_probe("GetFrontTyreParameters", "GetFrontTyreParameters"),
        make_function_probe("GetRearTyreParameters", "GetRearTyreParameters"),
    }

    return {
        schemaVersion = INVENTORY_SCHEMA_VERSION,
        exporterVersion = EXPORTER_VERSION,
        exportedAtUtc = EXPORT_TIMESTAMP_PLACEHOLDER,
        scope = "controlled-field-inventory",
        fields = json_array(fields),
        functions = json_array(functions),
        diagnostics = json_array({
            "documented_functions_not_called_without_protected_lua_calls",
        }),
    }
end

function DoExport(CarCalculator, CarFile)
    CarCalculatorGlobal = CarCalculator

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

    local last_access_time, last_access_time_path = read_first_number(CarCalculator, {
        "lastAccessTime",
        "LastAccessTime",
        "CarInfo.lastAccessTime",
        "CarInfo.LastAccessTime",
    })

    if model_name == nil then
        diagnostics[#diagnostics + 1] = "model_name_not_found"
    end

    if trim_name == nil then
        diagnostics[#diagnostics + 1] = "trim_name_not_found"
    end

    if automation_version == nil then
        diagnostics[#diagnostics + 1] = "automation_version_not_exposed"
    end

    if last_access_time == nil then
        diagnostics[#diagnostics + 1] = "last_access_time_not_found"
    end

    local document = {
        diagnostics = json_array(diagnostics),
        exportedAtUtc = EXPORT_TIMESTAMP_PLACEHOLDER,
        exporterVersion = EXPORTER_VERSION,
        schemaVersion = SCHEMA_VERSION,
        source = {
            automationVersion = value_or_null(automation_version),
            automationVersionPath = value_or_null(automation_version_path),
            kind = "Automation",
            lastAccessTime = value_or_null(last_access_time),
            lastAccessTimePath = value_or_null(last_access_time_path),
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
        [INVENTORY_OUTPUT_FILENAME] = encode_json(build_inventory()) .. "\n",
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
