#!/usr/bin/env julia
# Solve a Sienna PSY-JSON system with PowerSimulations.jl and write a small JSON
# result summary. Invoked as a subprocess by sienna_mcp.tools.solve_tools.run_sienna_solve
# -- see SIENNA/sienna_mcp/_julia.py for the process-launch mechanism (mirrors HOPE's).
#
# Usage:
#   julia solve_system.jl <psy_json_path> <output_json_path> [solver] [horizon_hours]
#
# solver: currently only "HiGHS" (open-source, MIT-licensed MILP/LP solver) is
# wired up, matching the open-source-only constraint in issue #54 ("without a
# PLEXOS license or vendor network call anywhere in this connector").

using Dates
using JSON3
using PowerSystems
using PowerSimulations
using HiGHS

const PSY = PowerSystems
const PSI = PowerSimulations

function build_template(sys::PSY.System)
    template = PSI.ProblemTemplate()
    PSI.set_network_model!(template, PSI.NetworkModel(PSI.CopperPlatePowerModel))
    if !isempty(PSY.get_components(PSY.ThermalStandard, sys))
        PSI.set_device_model!(template, PSY.ThermalStandard, PSI.ThermalBasicDispatch)
    end
    if !isempty(PSY.get_components(PSY.RenewableDispatch, sys))
        PSI.set_device_model!(template, PSY.RenewableDispatch, PSI.RenewableFullDispatch)
    end
    if !isempty(PSY.get_components(PSY.PowerLoad, sys))
        PSI.set_device_model!(template, PSY.PowerLoad, PSI.StaticPowerLoad)
    end
    return template
end

function main()
    args = ARGS
    length(args) >= 2 || error(
        "usage: solve_system.jl <psy_json_path> <output_json_path> [solver] [horizon_hours]",
    )
    psy_json_path = args[1]
    output_json_path = args[2]
    solver = length(args) >= 3 ? args[3] : "HiGHS"
    horizon_hours = length(args) >= 4 ? parse(Int, args[4]) : 24

    result = Dict{String, Any}(
        "psy_json_path" => psy_json_path,
        "solver" => solver,
        "horizon_hours" => horizon_hours,
    )

    try
        sys = PSY.System(psy_json_path)
        result["component_count"] = length(collect(PSY.get_components(PSY.Component, sys)))

        if solver != "HiGHS"
            error("Unsupported solver '$solver'; only the open-source HiGHS solver is wired up.")
        end

        # PowerSimulations needs Deterministic forecasts, not raw SingleTimeSeries;
        # this is the standard Sienna workflow step (see PSY/PSI tutorials) that
        # turns any attached SingleTimeSeries into horizon-length forecast windows.
        # Systems with no time series at all (a bare topology/definition export)
        # cannot be solved for production cost -- transform_single_time_series!
        # raises in that case, which the outer catch below reports as an error
        # rather than a silent no-op.
        PSY.transform_single_time_series!(sys, Dates.Hour(horizon_hours), Dates.Hour(horizon_hours))

        template = build_template(sys)
        model = PSI.DecisionModel(
            template,
            sys;
            optimizer = HiGHS.Optimizer,
            horizon = Dates.Hour(horizon_hours),
            name = "sienna_mcp_solve",
        )

        build_status = PSI.build!(model; output_dir = mktempdir())
        result["build_status"] = string(build_status)

        solve_status = PSI.solve!(model)
        result["solve_status"] = string(solve_status)

        result["ok"] = string(solve_status) in ("SUCCESSFULLY_FINALIZED", "SUCCESSFUL")

        try
            stats = PSI.get_optimizer_stats(model)
            result["objective_value"] = stats.objective_value
            result["solve_time_sec"] = stats.solve_time
        catch e
            result["optimizer_stats_error"] = sprint(showerror, e)
        end
    catch e
        result["ok"] = false
        result["error"] = sprint(showerror, e)
        result["error_type"] = string(typeof(e))
    end

    open(output_json_path, "w") do io
        JSON3.write(io, result)
    end

    println(result["ok"] ? "SIENNA_SOLVE_OK" : "SIENNA_SOLVE_FAILED")
end

main()
