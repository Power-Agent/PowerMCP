"""EvEMTBench catalogs and guarded component builders for PowerFactory."""

import hashlib
import inspect
import json
import math
import random
from typing import Any, Optional, get_args


class EvEMTBenchMixin:
    _evemtbench_creators = {
        "transformer": "create_evemtbench_transformer",
        "overhead_line": "create_evemtbench_line",
        "underground_cable": "create_evemtbench_cable",
        "external_grid": "create_evemtbench_external_grid",
        "load": "create_evemtbench_load",
        "synchronous_machine": "create_evemtbench_synchronous_machine",
    }

    @staticmethod
    def _evemtbench_parameter_schema(method):
        schema = {}
        types = {str: "string", float: "number", int: "integer", bool: "boolean"}
        for name, parameter in inspect.signature(method).parameters.items():
            if name.startswith("_"):
                continue
            annotation = parameter.annotation
            arguments = get_args(annotation)
            nullable = type(None) in arguments
            if nullable:
                annotation = next(arg for arg in arguments if arg is not type(None))
            entry = {
                "type": types.get(annotation, str(annotation)),
                "required": parameter.default is inspect.Parameter.empty,
            }
            if nullable:
                entry["nullable"] = True
            if parameter.default is not inspect.Parameter.empty:
                entry["default"] = parameter.default
            schema[name] = entry
        return schema

    @classmethod
    def list_evemtbench_components(cls, component_type: str, filters=None):
        """List one component catalog and its creation inputs without PowerFactory."""
        listings = {
            "transformer": "list_evemtbench_transformer_profiles",
            "overhead_line": "list_evemtbench_line_profiles",
            "underground_cable": "list_evemtbench_cable_profiles",
            "external_grid": "list_evemtbench_external_grid_profiles",
            "load": "list_evemtbench_load_profiles",
            "synchronous_machine": "list_evemtbench_synchronous_machine_profiles",
        }
        kind = str(component_type or "").strip().lower().replace("-", "_")
        if kind not in listings:
            return {
                "success": False,
                "component_type": kind,
                "supported_component_types": list(listings),
                "message": "component_type must be one of: " + ", ".join(listings),
            }
        listing = getattr(cls, listings[kind])
        metadata = {
            "component_type": kind,
            "available_filters": cls._evemtbench_parameter_schema(listing),
            "creation_parameters": cls._evemtbench_parameter_schema(
                getattr(cls, cls._evemtbench_creators[kind])
            ),
        }
        if filters is None:
            filters = {}
        if not isinstance(filters, dict):
            return {"success": False, "message": "filters must be an object", **metadata}
        try:
            inspect.signature(listing).bind(**filters)
        except TypeError as exc:
            return {"success": False, "message": f"Invalid {kind} filters: {exc}", **metadata}
        return {**listing(**filters), **metadata}

    @classmethod
    def _rollback_equipment_type(cls, equipment_folder, created_type,
                                 created_folder, type_name, type_class, folder_name):
        """Remove only objects made by this call and report survivors."""
        remaining_type = False
        remaining_folder = False
        if created_type is not None:
            try:
                created_type.Delete()
            except Exception:
                pass
            try:
                remaining_type = bool(cls._find_named_contents(
                    equipment_folder, type_name, type_class,
                ))
            except Exception:
                remaining_type = True
        if created_folder is not None:
            try:
                if not (created_folder.GetContents("*", 0) or []):
                    created_folder.Delete()
            except Exception:
                pass
            try:
                remaining_folder = bool(cls._find_named_contents(
                    equipment_folder, folder_name, "IntPrjfolder",
                ))
            except Exception:
                remaining_folder = True
        rolled_back = None
        if created_type is not None or created_folder is not None:
            rolled_back = not remaining_type and not remaining_folder
        return {
            "rolled_back": rolled_back,
            "type_created": remaining_type,
            "remaining_type": type_name if remaining_type else None,
        }

    @staticmethod
    def _creation_confirmation_token(readable_prefix: str, plan: dict[str, Any]) -> str:
        """Bind confirmation to a canonical, lossless representation of the plan."""
        canonical_plan = json.dumps(
            plan,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        digest = hashlib.sha256(canonical_plan.encode("utf-8")).hexdigest()
        return f"{readable_prefix} plan={digest}"

    @staticmethod
    def _find_named_contents(parent, name: str, class_name: str):
        requested = str(name or "").strip()
        # GetContents name patterns are case-sensitive; match names in Python.
        return [
            obj
            for obj in (
                parent.GetContents(f"*.{class_name}", 1) or []
            )
            if str(obj.GetAttribute("loc_name")).casefold()
            == requested.casefold()
        ]

    @classmethod
    def _load_evemtbench_database(cls):
        """Load and validate the versioned transformer source database."""
        with open(cls._evemtbench_database_file, "r", encoding="utf-8") as stream:
            database = json.load(stream)

        if database.get("schema_version") != 1:
            raise RuntimeError("Unsupported EvEMTBench database schema")
        classes = database.get("classes")
        vector_groups = database.get("vector_groups")
        if not isinstance(classes, dict) or not classes:
            raise RuntimeError("EvEMTBench database has no transformer classes")
        if not isinstance(vector_groups, dict) or not vector_groups:
            raise RuntimeError("EvEMTBench database has no vector groups")
        frequencies = database.get("sampling", {}).get(
            "nominal_frequencies_hz"
        )
        if frequencies != [50.0, 60.0]:
            raise RuntimeError("EvEMTBench database has invalid frequencies")

        def validate_spec(spec, label):
            if not isinstance(spec, dict):
                raise RuntimeError(f"Invalid numeric specification: {label}")
            if set(spec) == {"value"}:
                values = (spec["value"],)
            elif set(spec) == {"min", "max"}:
                values = (spec["min"], spec["max"])
                if float(values[0]) > float(values[1]):
                    raise RuntimeError(f"Invalid interval ordering: {label}")
            else:
                raise RuntimeError(f"Invalid numeric specification: {label}")
            if any(
                isinstance(value, bool) or not math.isfinite(float(value))
                for value in values
            ):
                raise RuntimeError(f"Non-finite database value: {label}")

        parameter_names = (
            "short_circuit_voltage_pct",
            "winding_losses_kw",
            "no_load_losses_kw",
            "no_load_current_pct",
        )
        for class_name, transformer_class in classes.items():
            for voltage_name in ("high_voltage_kv", "low_voltage_kv"):
                voltage = transformer_class.get(voltage_name)
                if (
                    isinstance(voltage, bool)
                    or not math.isfinite(float(voltage))
                    or float(voltage) <= 0
                ):
                    raise RuntimeError(
                        f"Invalid {voltage_name} for transformer class {class_name}"
                    )
            ratings = transformer_class.get("ratings")
            if not isinstance(ratings, list) or not ratings:
                raise RuntimeError(
                    f"No ratings for transformer class {class_name}"
                )
            seen_ratings = set()
            for index, rating in enumerate(ratings):
                rated_power = float(rating.get("rated_power_mva"))
                if not math.isfinite(rated_power) or rated_power <= 0:
                    raise RuntimeError(
                        f"Invalid rating for transformer class {class_name}"
                    )
                if rated_power in seen_ratings:
                    raise RuntimeError(
                        f"Duplicate rating for transformer class {class_name}: "
                        f"{rated_power:g}"
                    )
                seen_ratings.add(rated_power)
                for parameter_name in parameter_names:
                    validate_spec(
                        rating.get(parameter_name),
                        f"{class_name}.ratings[{index}].{parameter_name}",
                    )
                groups = rating.get("vector_groups")
                if not isinstance(groups, list) or not groups:
                    raise RuntimeError(
                        f"No vector group for {class_name} rating {rated_power:g}"
                    )
                unknown = sorted(set(groups) - set(vector_groups))
                if unknown:
                    raise RuntimeError(
                        f"Unknown vector group(s): {', '.join(unknown)}"
                    )
        return database

    @classmethod
    def _load_evemtbench_sequence_database(cls, path: str, label: str):
        """Load and validate a versioned line/cable sequence database."""
        with open(path, "r", encoding="utf-8") as stream:
            database = json.load(stream)

        if database.get("schema_version") != 1:
            raise RuntimeError(
                f"Unsupported EvEMTBench {label} database schema"
            )
        if database.get("nominal_frequencies_hz") != [50.0, 60.0]:
            raise RuntimeError(
                f"EvEMTBench {label} database has invalid frequencies"
            )
        profiles = database.get("profiles")
        if profiles != ["p05", "p50", "p95"]:
            raise RuntimeError(
                f"EvEMTBench {label} database has invalid profiles"
            )
        classes = database.get("classes")
        if not isinstance(classes, dict) or not classes:
            raise RuntimeError(
                f"EvEMTBench {label} database has no voltage classes"
            )

        parameter_names = (
            "r1_ohm_per_km",
            "x1_ohm_per_km",
            "c1_nf_per_km",
            "r0_ohm_per_km",
            "x0_ohm_per_km",
            "c0_nf_per_km",
        )
        for class_name, line_class in classes.items():
            voltage = float(line_class.get("nominal_voltage_kv"))
            if not math.isfinite(voltage) or voltage <= 0:
                raise RuntimeError(
                    f"Invalid nominal voltage for line class {class_name}"
                )
            length = line_class.get("length_km")
            if (
                not isinstance(length, dict)
                or set(length) != {"min", "max"}
                or float(length["min"]) <= 0
                or float(length["min"]) > float(length["max"])
            ):
                raise RuntimeError(
                    f"Invalid length range for line class {class_name}"
                )
            electrical = line_class.get("electrical_profiles")
            if not isinstance(electrical, dict) or list(electrical) != profiles:
                raise RuntimeError(
                    f"Invalid electrical profiles for line class {class_name}"
                )
            for profile_name, profile in electrical.items():
                if set(profile) != set(parameter_names):
                    raise RuntimeError(
                        f"Invalid {profile_name} fields for line class "
                        f"{class_name}"
                    )
                if any(
                    not math.isfinite(float(profile[name]))
                    or float(profile[name]) < 0
                    for name in parameter_names
                ):
                    raise RuntimeError(
                        f"Invalid {profile_name} values for line class "
                        f"{class_name}"
                    )
        return database

    @classmethod
    def _load_evemtbench_line_database(cls):
        """Load and validate the versioned overhead-line source database."""
        return cls._load_evemtbench_sequence_database(
            cls._evemtbench_line_database_file,
            "line",
        )

    @classmethod
    def _load_evemtbench_cable_database(cls):
        """Load and validate the versioned underground-cable database."""
        return cls._load_evemtbench_sequence_database(
            cls._evemtbench_cable_database_file,
            "cable",
        )

    @classmethod
    def _load_evemtbench_external_grid_database(cls):
        """Load and validate the versioned external-grid source database."""
        with open(
            cls._evemtbench_external_grid_database_file,
            "r",
            encoding="utf-8",
        ) as stream:
            database = json.load(stream)

        if database.get("schema_version") != 1:
            raise RuntimeError(
                "Unsupported EvEMTBench external-grid database schema"
            )
        classes = database.get("classes")
        if not isinstance(classes, dict) or not classes:
            raise RuntimeError(
                "EvEMTBench external-grid database has no voltage classes"
            )
        parameters = (
            "short_circuit_power_mva",
            "positive_sequence_r_x",
            "x0_x1",
            "zero_sequence_r_x",
            "voltage_setpoint_pu",
            "initial_phase_angle_deg",
        )
        seen_voltages = set()
        for class_name, source_class in classes.items():
            voltages = source_class.get("nominal_voltages_kv")
            if not isinstance(voltages, list) or not voltages:
                raise RuntimeError(
                    f"No nominal voltages for external-grid class {class_name}"
                )
            for raw_voltage in voltages:
                voltage = float(raw_voltage)
                if not math.isfinite(voltage) or voltage <= 0:
                    raise RuntimeError(
                        f"Invalid nominal voltage for external-grid class "
                        f"{class_name}"
                    )
                if voltage in seen_voltages:
                    raise RuntimeError(
                        f"Duplicate external-grid voltage: {voltage:g}"
                    )
                seen_voltages.add(voltage)
            for parameter in parameters:
                interval = source_class.get(parameter)
                if (
                    not isinstance(interval, dict)
                    or set(interval) != {"min", "max"}
                ):
                    raise RuntimeError(
                        f"Invalid {parameter} interval for external-grid "
                        f"class {class_name}"
                    )
                lower = float(interval["min"])
                upper = float(interval["max"])
                if (
                    not math.isfinite(lower)
                    or not math.isfinite(upper)
                    or lower > upper
                ):
                    raise RuntimeError(
                        f"Invalid {parameter} interval for external-grid "
                        f"class {class_name}"
                    )
                if parameter != "initial_phase_angle_deg" and lower <= 0:
                    raise RuntimeError(
                        f"Invalid {parameter} interval for external-grid "
                        f"class {class_name}"
                    )
        return database

    @classmethod
    def _load_evemtbench_load_database(cls):
        """Load and validate the versioned Table 5 load database."""
        with open(
            cls._evemtbench_load_database_file,
            "r",
            encoding="utf-8",
        ) as stream:
            database = json.load(stream)

        if database.get("schema_version") != 1:
            raise RuntimeError("Unsupported EvEMTBench load database schema")
        classes = database.get("classes")
        if not isinstance(classes, dict) or not classes:
            raise RuntimeError("EvEMTBench load database has no voltage classes")
        seen_voltages = set()
        for class_name, load_class in classes.items():
            voltage = float(load_class.get("nominal_voltage_kv"))
            if not math.isfinite(voltage) or voltage <= 0:
                raise RuntimeError(
                    f"Invalid nominal voltage for load class {class_name}"
                )
            if voltage in seen_voltages:
                raise RuntimeError(f"Duplicate load voltage: {voltage:g}")
            seen_voltages.add(voltage)

            if voltage == 20.0:
                intervals = ("apparent_power_mva",)
            else:
                intervals = (
                    "active_power_mw",
                    "reactive_power_mvar",
                )
            for parameter in intervals:
                interval = load_class.get(parameter)
                if (
                    not isinstance(interval, dict)
                    or set(interval) != {"min", "max"}
                ):
                    raise RuntimeError(
                        f"Invalid {parameter} interval for load class "
                        f"{class_name}"
                    )
                lower = float(interval["min"])
                upper = float(interval["max"])
                if (
                    not math.isfinite(lower)
                    or not math.isfinite(upper)
                    or lower < 0
                    or lower > upper
                ):
                    raise RuntimeError(
                        f"Invalid {parameter} interval for load class "
                        f"{class_name}"
                    )

        power_factor = database.get("twenty_kv_power_factor")
        if not isinstance(power_factor, dict):
            raise RuntimeError("EvEMTBench load database has no power factor")
        inductive = float(power_factor.get("inductive_min"))
        capacitive = float(power_factor.get("capacitive_min"))
        if not 0 < inductive <= 1 or not 0 < capacitive <= 1:
            raise RuntimeError("EvEMTBench load database has invalid power factor")
        return database

    @classmethod
    def _load_evemtbench_synchronous_machine_database(cls):
        """Load and validate the versioned Table 13 machine catalog."""
        with open(
            cls._evemtbench_synchronous_machine_database_file,
            "r",
            encoding="utf-8",
        ) as stream:
            database = json.load(stream)

        if database.get("schema_version") != 1:
            raise RuntimeError(
                "Unsupported EvEMTBench synchronous-machine database schema"
            )
        classes = database.get("classes")
        if not isinstance(classes, dict) or set(classes) != {
            "salient_pole",
            "round_rotor",
        }:
            raise RuntimeError(
                "EvEMTBench synchronous-machine database must contain "
                "salient_pole and round_rotor classes"
            )
        for class_name, profile in classes.items():
            for parameter in (
                "rated_apparent_power_mva",
                "rated_power_factor",
            ):
                interval = profile.get(parameter)
                if (
                    not isinstance(interval, dict)
                    or set(interval) != {"min", "max"}
                ):
                    raise RuntimeError(
                        f"Invalid {parameter} interval for synchronous-machine "
                        f"class {class_name}"
                    )
                lower = float(interval["min"])
                upper = float(interval["max"])
                if (
                    not math.isfinite(lower)
                    or not math.isfinite(upper)
                    or lower <= 0
                    or lower > upper
                ):
                    raise RuntimeError(
                        f"Invalid {parameter} interval for synchronous-machine "
                        f"class {class_name}"
                    )
            if not isinstance(profile.get("parameters"), dict):
                raise RuntimeError(
                    f"Synchronous-machine class {class_name} has no parameters"
                )
        rules = database.get("rated_voltage_rule")
        if not isinstance(rules, list) or len(rules) != 4:
            raise RuntimeError(
                "EvEMTBench synchronous-machine voltage rule is invalid"
            )
        return database

    @classmethod
    def list_evemtbench_line_profiles(
        cls,
        voltage_kv: Optional[float] = None,
        profile: str = "",
    ) -> dict[str, Any]:
        """List executable overhead-line profiles without opening PowerFactory."""
        try:
            database = cls._load_evemtbench_line_database()
            requested_profile = str(profile or "").strip().lower()
            if requested_profile and requested_profile not in database["profiles"]:
                return {
                    "success": False,
                    "message": "profile must be one of: "
                    + ", ".join(database["profiles"]),
                }

            if voltage_kv is None:
                selected = database["classes"]
            else:
                if isinstance(voltage_kv, bool):
                    return {
                        "success": False,
                        "message": "voltage_kv must be a number",
                    }
                requested_voltage = float(voltage_kv)
                selected = {
                    name: value
                    for name, value in database["classes"].items()
                    if math.isclose(
                        float(value["nominal_voltage_kv"]),
                        requested_voltage,
                    )
                }
                if not selected:
                    available = ", ".join(database["classes"])
                    return {
                        "success": False,
                        "message": "voltage_kv must be one of: " + available,
                    }

            results = []
            for class_name, line_class in selected.items():
                item = {
                    "voltage_class": class_name,
                    "nominal_voltage_kv": line_class["nominal_voltage_kv"],
                    "length_km": line_class["length_km"],
                    "electrical_profiles": line_class["electrical_profiles"],
                }
                if requested_profile:
                    item["electrical_profiles"] = {
                        requested_profile: line_class["electrical_profiles"][
                            requested_profile
                        ]
                    }
                if "rated_current_guidance_ka" in line_class:
                    item["rated_current_guidance_ka"] = line_class[
                        "rated_current_guidance_ka"
                    ]
                results.append(item)
            return {
                "success": True,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "component_type": "overhead_line_sequence_equivalent",
                "nominal_frequencies_hz": database[
                    "nominal_frequencies_hz"
                ],
                "returned_count": len(results),
                "results": results,
                "powerfactory": database["powerfactory"],
                "catalog_only": database["catalog_only"],
            }
        except (TypeError, ValueError):
            return {"success": False, "message": "voltage_kv must be a number"}
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    @classmethod
    def list_evemtbench_cable_profiles(
        cls,
        profile: str = "",
    ) -> dict[str, Any]:
        """List executable 20 kV cable profiles without PowerFactory."""
        try:
            database = cls._load_evemtbench_cable_database()
            requested_profile = str(profile or "").strip().lower()
            if requested_profile and requested_profile not in database["profiles"]:
                return {
                    "success": False,
                    "message": "profile must be one of: "
                    + ", ".join(database["profiles"]),
                }

            cable_class = database["classes"]["20"]
            electrical = cable_class["electrical_profiles"]
            if requested_profile:
                electrical = {requested_profile: electrical[requested_profile]}
            return {
                "success": True,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "component_type": "underground_cable_sequence_equivalent",
                "nominal_frequencies_hz": database[
                    "nominal_frequencies_hz"
                ],
                "returned_count": 1,
                "results": [{
                    "voltage_class": "20",
                    "nominal_voltage_kv": cable_class["nominal_voltage_kv"],
                    "length_km": cable_class["length_km"],
                    "electrical_profiles": electrical,
                }],
                "construction": database["construction"],
                "powerfactory": database["powerfactory"],
                "catalog_only": database["catalog_only"],
            }
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    @classmethod
    def _evemtbench_line_plan(
        cls,
        voltage_kv: float,
        nominal_frequency_hz: float,
        rated_current_ka: float,
        profile: str,
        type_name: str,
    ):
        database = cls._load_evemtbench_line_database()
        class_name, line_class = next(
            (
                (name, value)
                for name, value in database["classes"].items()
                if math.isclose(
                    float(value["nominal_voltage_kv"]),
                    voltage_kv,
                )
            ),
            (None, None),
        )
        if line_class is None:
            raise RuntimeError(
                "voltage_kv must be one of: "
                + ", ".join(database["classes"])
            )
        if profile not in database["profiles"]:
            raise RuntimeError(
                "profile must be one of: " + ", ".join(database["profiles"])
            )
        values = line_class["electrical_profiles"][profile]
        capacitance_factor = float(
            database["powerfactory"]["capacitance_conversion_factor"]
        )
        attributes = {
            "uline": voltage_kv,
            "sline": rated_current_ka,
            "frnom": nominal_frequency_hz,
            "rline": float(values["r1_ohm_per_km"]),
            "xline": float(values["x1_ohm_per_km"]),
            "cline": float(values["c1_nf_per_km"]) * capacitance_factor,
            "rline0": float(values["r0_ohm_per_km"]),
            "xline0": float(values["x0_ohm_per_km"]),
            "cline0": float(values["c0_nf_per_km"]) * capacitance_factor,
        }
        return class_name, line_class, {
            "name": type_name,
            "catalog_id": database["catalog_id"],
            "source_tables": line_class["source_tables"],
            "profile": profile,
            "parameters": {
                "nominal_voltage_kv": voltage_kv,
                "nominal_frequency_hz": nominal_frequency_hz,
                "rated_current_ka": rated_current_ka,
                **values,
            },
            "powerfactory_attributes": attributes,
            "capacitance_conversion": "nF/km to uF/km (multiply by 0.001)",
            "model": database["powerfactory"]["model"],
        }

    @classmethod
    def _evemtbench_cable_plan(
        cls,
        voltage_kv: float,
        nominal_frequency_hz: float,
        rated_current_ka: float,
        profile: str,
        type_name: str,
    ):
        database = cls._load_evemtbench_cable_database()
        cable_class = database["classes"].get("20")
        if cable_class is None or not math.isclose(voltage_kv, 20.0):
            raise RuntimeError("voltage_kv must be 20 for underground cables")
        if profile not in database["profiles"]:
            raise RuntimeError(
                "profile must be one of: " + ", ".join(database["profiles"])
            )
        values = cable_class["electrical_profiles"][profile]
        capacitance_factor = float(
            database["powerfactory"]["capacitance_conversion_factor"]
        )
        attributes = {
            "uline": 20.0,
            "sline": rated_current_ka,
            "frnom": nominal_frequency_hz,
            "rline": float(values["r1_ohm_per_km"]),
            "xline": float(values["x1_ohm_per_km"]),
            "cline": float(values["c1_nf_per_km"]) * capacitance_factor,
            "rline0": float(values["r0_ohm_per_km"]),
            "xline0": float(values["x0_ohm_per_km"]),
            "cline0": float(values["c0_nf_per_km"]) * capacitance_factor,
        }
        return "20", cable_class, {
            "name": type_name,
            "catalog_id": database["catalog_id"],
            "source_tables": cable_class["source_tables"],
            "profile": profile,
            "parameters": {
                "nominal_voltage_kv": 20.0,
                "nominal_frequency_hz": nominal_frequency_hz,
                "rated_current_ka": rated_current_ka,
                **values,
            },
            "powerfactory_attributes": attributes,
            "capacitance_conversion": "nF/km to uF/km (multiply by 0.001)",
            "model": database["powerfactory"]["model"],
            "construction_catalog": database["construction"],
        }

    @classmethod
    def list_evemtbench_external_grid_profiles(
        cls,
        voltage_kv: Optional[float] = None,
    ) -> dict[str, Any]:
        """List executable Table 4 profiles without opening PowerFactory."""
        try:
            database = cls._load_evemtbench_external_grid_database()
            selected = []
            if voltage_kv is None:
                selected = list(database["classes"].items())
            else:
                if isinstance(voltage_kv, bool):
                    raise ValueError
                requested = float(voltage_kv)
                selected = [
                    (name, source_class)
                    for name, source_class in database["classes"].items()
                    if any(
                        math.isclose(float(value), requested)
                        for value in source_class["nominal_voltages_kv"]
                    )
                ]
                if not selected:
                    available = sorted(
                        float(value)
                        for source_class in database["classes"].values()
                        for value in source_class["nominal_voltages_kv"]
                    )
                    return {
                        "success": False,
                        "message": "voltage_kv must be one of: "
                        + ", ".join(f"{value:g}" for value in available),
                    }
            results = [
                {
                    "voltage_class": class_name,
                    **source_class,
                }
                for class_name, source_class in selected
            ]
            return {
                "success": True,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "component_type": "external_grid_equivalent",
                "returned_count": len(results),
                "results": results,
                "powerfactory": database["powerfactory"],
            }
        except (TypeError, ValueError):
            return {"success": False, "message": "voltage_kv must be a number"}
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    @classmethod
    def _evemtbench_external_grid_plan(
        cls,
        voltage_kv: float,
        external_grid_name: str,
        seed: int,
    ):
        database = cls._load_evemtbench_external_grid_database()
        class_name, source_class = next(
            (
                (name, value)
                for name, value in database["classes"].items()
                if any(
                    math.isclose(float(candidate), voltage_kv)
                    for candidate in value["nominal_voltages_kv"]
                )
            ),
            (None, None),
        )
        if source_class is None:
            available = sorted(
                float(value)
                for value in (
                    candidate
                    for item in database["classes"].values()
                    for candidate in item["nominal_voltages_kv"]
                )
            )
            raise RuntimeError(
                "voltage_kv must be one of: "
                + ", ".join(f"{value:g}" for value in available)
            )
        rng = random.Random(seed)

        def sampled(parameter):
            interval = source_class[parameter]
            return round(
                rng.uniform(float(interval["min"]), float(interval["max"])),
                6,
            )

        parameters = {
            "nominal_voltage_kv": voltage_kv,
            "short_circuit_power_mva": sampled(
                "short_circuit_power_mva"
            ),
            "positive_sequence_r_x": sampled("positive_sequence_r_x"),
            "x0_x1": sampled("x0_x1"),
            "zero_sequence_r_x": sampled("zero_sequence_r_x"),
            "voltage_setpoint_pu": sampled("voltage_setpoint_pu"),
            "initial_phase_angle_deg": sampled("initial_phase_angle_deg"),
        }
        attributes = {
            "bustp": "SL",
            "snss": parameters["short_circuit_power_mva"],
            "rntxn": parameters["positive_sequence_r_x"],
            "x0tx1": parameters["x0_x1"],
            "r0tx0": parameters["zero_sequence_r_x"],
            "usetp": parameters["voltage_setpoint_pu"],
            "phiini": parameters["initial_phase_angle_deg"],
        }
        return class_name, {
            "name": external_grid_name,
            "catalog_id": database["catalog_id"],
            "source_tables": database["source"]["tables"],
            "voltage_class": class_name,
            "seed": seed,
            "parameters": parameters,
            "powerfactory_attributes": attributes,
            "model": database["powerfactory"]["model"],
        }

    @classmethod
    def list_evemtbench_load_profiles(
        cls,
        voltage_kv: Optional[float] = None,
    ) -> dict[str, Any]:
        """List executable Table 5 load-power profiles."""
        try:
            database = cls._load_evemtbench_load_database()
            classes = database["classes"]
            if voltage_kv is None:
                selected = classes.items()
            else:
                if isinstance(voltage_kv, bool):
                    raise ValueError
                requested = float(voltage_kv)
                selected = [
                    (name, profile)
                    for name, profile in classes.items()
                    if math.isclose(
                        float(profile["nominal_voltage_kv"]),
                        requested,
                    )
                ]
                if not selected:
                    return {
                        "success": False,
                        "message": "voltage_kv must be one of: "
                        + ", ".join(classes),
                    }
            results = [
                {"voltage_class": name, **profile}
                for name, profile in selected
            ]
            return {
                "success": True,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "component_type": "balanced_load",
                "returned_count": len(results),
                "results": results,
                "twenty_kv_power_factor": database[
                    "twenty_kv_power_factor"
                ],
                "powerfactory": database["powerfactory"],
                "catalog_only": database["catalog_only"],
            }
        except (TypeError, ValueError):
            return {"success": False, "message": "voltage_kv must be a number"}
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    @classmethod
    def list_evemtbench_synchronous_machine_profiles(
        cls,
        machine_type: str = "",
    ) -> dict[str, Any]:
        """List captured Table 13 profiles without opening PowerFactory."""
        try:
            database = cls._load_evemtbench_synchronous_machine_database()
            requested = str(machine_type or "").strip().lower()
            classes = database["classes"]
            if requested and requested not in classes:
                return {
                    "success": False,
                    "message": "machine_type must be one of: "
                    + ", ".join(classes),
                }
            selected = (
                [(requested, classes[requested])]
                if requested
                else classes.items()
            )
            return {
                "success": True,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "component_type": "synchronous_machine",
                "returned_count": len(selected),
                "rated_voltage_rule": database["rated_voltage_rule"],
                "results": [
                    {"machine_type": name, **profile}
                    for name, profile in selected
                ],
                "powerfactory": database["powerfactory"],
            }
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    @classmethod
    def _evemtbench_synchronous_machine_plan(
        cls,
        machine_type: str,
        rated_power_mva: float,
        type_name: str,
        seed: int,
    ):
        database = cls._load_evemtbench_synchronous_machine_database()
        if machine_type != "round_rotor":
            if machine_type == "salient_pole":
                raise RuntimeError(
                    "salient_pole is catalog-only because Table 13 does not "
                    "provide xq transient data"
                )
            raise RuntimeError(
                "machine_type must be one of: round_rotor"
            )

        profile = database["classes"][machine_type]
        power_range = profile["rated_apparent_power_mva"]
        if not (
            float(power_range["min"])
            <= rated_power_mva
            <= float(power_range["max"])
        ):
            raise RuntimeError(
                "rated_power_mva must be between "
                f"{power_range['min']:g} and {power_range['max']:g} "
                "for round_rotor"
            )

        rated_voltage = next(
            float(rule["rated_voltage_kv"])
            for rule in database["rated_voltage_rule"]
            if rule["maximum_rated_power_mva"] is None
            or rated_power_mva
            <= float(rule["maximum_rated_power_mva"])
        )
        parameters = profile["parameters"]
        rng = random.Random(seed)

        def sampled(spec, lower=None, upper=None):
            minimum = float(spec["min"] if lower is None else lower)
            maximum = float(spec["max"] if upper is None else upper)
            if minimum > maximum:
                raise RuntimeError(
                    "Table 13 dependency constraints produced an empty "
                    "sampling interval"
                )
            return round(rng.uniform(minimum, maximum), 6)

        xdss = sampled(parameters["xd_subtransient_pu"])
        xqss_multiplier = sampled(
            parameters[
                "xq_subtransient_multiplier_of_xd_subtransient"
            ]
        )
        xqss = round(xdss * xqss_multiplier, 6)
        xds_spec = parameters["xd_transient_pu"]
        xds = sampled(
            xds_spec,
            max(
                float(xds_spec["min"]),
                float(xds_spec["minimum_multiplier_of_xd_subtransient"])
                * xdss,
                1.01 * xqss,
            ),
            float(xds_spec["max"]),
        )
        xqs_spec = parameters[
            "xq_transient_multiplier_of_xd_transient"
        ]
        xqs = sampled(
            xqs_spec,
            max(
                float(xqs_spec["min"]) * xds,
                float(xqs_spec["minimum_multiplier_of_xq_subtransient"])
                * xqss,
            ),
            float(xqs_spec["max"]) * xds,
        )
        xd_spec = parameters["xd_synchronous_pu"]
        xd = sampled(
            xd_spec,
            max(
                float(xd_spec["min"]),
                float(xd_spec["minimum_multiplier_of_xd_transient"])
                * xds,
            ),
            float(xd_spec["max"]),
        )
        xq_spec = parameters[
            "xq_synchronous_multiplier_of_xd_synchronous"
        ]
        xq = sampled(
            xq_spec,
            max(
                float(xq_spec["min"]) * xd,
                float(xq_spec["minimum_multiplier_of_xq_transient"])
                * xqs,
            ),
            float(xq_spec["max"]) * xd,
        )
        sg10 = sampled(parameters["saturation_factor_1_0_pu"])
        sg12_spec = parameters["saturation_factor_1_2_pu"]
        sg12 = sampled(
            sg12_spec,
            max(float(sg12_spec["min"]), sg10),
            float(sg12_spec["max"]),
        )
        xl_spec = parameters["leakage_reactance_pu"]
        xl = sampled(
            xl_spec,
            float(xl_spec["min"]),
            min(0.333, xdss, xqss),
        )
        x2_multiplier = sampled(
            parameters[
                "negative_sequence_reactance_multiplier_of_xd_subtransient"
            ]
        )
        source_parameters = {
            "rated_apparent_power_mva": rated_power_mva,
            "rated_voltage_kv": rated_voltage,
            "rated_power_factor": sampled(profile["rated_power_factor"]),
            "stator_resistance_pu": sampled(
                parameters["stator_resistance_pu"]
            ),
            "leakage_reactance_pu": xl,
            "xd_synchronous_pu": xd,
            "xq_synchronous_pu": xq,
            "xd_transient_pu": xds,
            "xq_transient_pu": xqs,
            "xd_subtransient_pu": xdss,
            "xq_subtransient_pu": xqss,
            "td_transient_s": sampled(parameters["td_transient_s"]),
            "tq_transient_s": sampled(parameters["tq_transient_s"]),
            "td_subtransient_s": sampled(
                parameters["td_subtransient_s"]
            ),
            "tq_subtransient_s": sampled(
                parameters["tq_subtransient_s"]
            ),
            "zero_sequence_reactance_pu": sampled(
                parameters["zero_sequence_reactance_pu"]
            ),
            "zero_sequence_resistance_pu": float(
                parameters["zero_sequence_resistance_pu"]["value"]
            ),
            "negative_sequence_reactance_pu": round(
                xdss * x2_multiplier,
                6,
            ),
            "negative_sequence_resistance_pu": sampled(
                parameters["negative_sequence_resistance_pu"]
            ),
            "acceleration_time_constant_s": sampled(
                parameters["acceleration_time_constant_s"]
            ),
            "saturation_mode": int(
                parameters["saturation_mode"]["value"]
            ),
            "saturation_factor_1_0_pu": sg10,
            "saturation_factor_1_2_pu": sg12,
            "reactive_power_max_pu": float(
                parameters["reactive_power_max_pu"]["value"]
            ),
            "reactive_power_min_pu": float(
                parameters["reactive_power_min_pu"]["value"]
            ),
        }
        mapped = database["powerfactory"]["mapped_attributes"]
        time_constant_inputs = {
            "td_transient_s": (
                source_parameters["td_transient_s"] * xd / xds
            ),
            "tq_transient_s": (
                source_parameters["tq_transient_s"] * xq / xqs
            ),
            "td_subtransient_s": (
                source_parameters["td_subtransient_s"] * xds / xdss
            ),
            "tq_subtransient_s": (
                source_parameters["tq_subtransient_s"] * xqs / xqss
            ),
        }
        attributes = {
            "iturbo": database["powerfactory"]["rotor_mode"][machine_type],
            **{
                mapped[name]: time_constant_inputs.get(name, value)
                for name, value in source_parameters.items()
            },
        }
        return {
            "name": type_name,
            "catalog_id": database["catalog_id"],
            "source_tables": database["source"]["tables"],
            "machine_type": machine_type,
            "seed": seed,
            "parameters": source_parameters,
            "powerfactory_attributes": attributes,
            "powerfactory_derived_attributes": {
                "tds": source_parameters["td_transient_s"],
                "tqs": source_parameters["tq_transient_s"],
                "tdss": source_parameters["td_subtransient_s"],
                "tqss": source_parameters["tq_subtransient_s"],
            },
        }

    @classmethod
    def _evemtbench_load_plan(
        cls,
        voltage_kv: float,
        load_name: str,
        seed: int,
        load_model: str = "constant_power",
    ):
        database = cls._load_evemtbench_load_database()
        class_name, profile = next(
            (
                (name, value)
                for name, value in database["classes"].items()
                if math.isclose(
                    float(value["nominal_voltage_kv"]),
                    voltage_kv,
                )
            ),
            (None, None),
        )
        if profile is None:
            raise RuntimeError(
                "voltage_kv must be one of: "
                + ", ".join(database["classes"])
            )
        rng = random.Random(seed)

        def sampled(interval):
            return rng.uniform(
                float(interval["min"]),
                float(interval["max"]),
            )

        if voltage_kv == 20.0:
            apparent_power = sampled(profile["apparent_power_mva"])
            power_factor = database["twenty_kv_power_factor"]
            capacitive_angle = -math.acos(
                float(power_factor["capacitive_min"])
            )
            inductive_angle = math.acos(
                float(power_factor["inductive_min"])
            )
            angle = rng.uniform(capacitive_angle, inductive_angle)
            active_power = apparent_power * math.cos(angle)
            reactive_power = apparent_power * math.sin(angle)
            source_parameters = {
                "apparent_power_mva": round(apparent_power, 6),
                "power_factor": round(math.cos(angle), 6),
                "power_factor_mode": (
                    "inductive" if angle >= 0 else "capacitive"
                ),
                "reactive_power_angle_deg": round(
                    math.degrees(angle),
                    6,
                ),
            }
        else:
            active_power = sampled(profile["active_power_mw"])
            reactive_power = sampled(profile["reactive_power_mvar"])
            source_parameters = {}

        active_power = round(active_power, 6)
        reactive_power = round(reactive_power, 6)
        item = {
            "name": load_name,
            "catalog_id": database["catalog_id"],
            "source_tables": database["source"]["tables"],
            "voltage_class": class_name,
            "seed": seed,
            "parameters": {
                "nominal_voltage_kv": voltage_kv,
                "active_power_mw": active_power,
                "reactive_power_mvar": reactive_power,
                **source_parameters,
            },
            "powerfactory_attributes": {
                "plini": active_power,
                "qlini": reactive_power,
            },
            "model": database["powerfactory"]["model"],
            "load_model": load_model,
            "catalog_only": database["catalog_only"],
        }

        if load_model == "zip":
            # A separate stream keeps the existing seeded P/Q samples unchanged.
            zip_rng = random.Random(f"evemtbench-load-zip:{seed}")
            specs = database["catalog_only"]["load_model_coefficients"]
            coefficients = {}
            for prefix in ("kP", "kQ"):
                bounds = []
                for term in ("Z", "I", "P"):
                    spec = specs[f"{prefix}_{term}"]
                    lo, hi = spec["min"], spec["max"]
                    if (isinstance(lo, bool) or isinstance(hi, bool)
                            or not math.isfinite(float(lo)) or not math.isfinite(float(hi))
                            or float(lo) > float(hi)):
                        raise RuntimeError("Invalid ZIP coefficient interval")
                    bounds.append((float(lo), float(hi)))
                (zmin, zmax), (imin, imax), (pmin, pmax) = bounds
                lower, upper = max(zmin, 1 - imax - pmax), min(zmax, 1 - imin - pmin)
                if lower > upper:
                    raise RuntimeError("ZIP coefficient constraints have no feasible solution")
                z = zip_rng.uniform(lower, upper)
                ilower, iupper = max(imin, 1 - z - pmax), min(imax, 1 - z - pmin)
                if ilower > iupper:
                    raise RuntimeError("ZIP current coefficient interval is empty")
                current = zip_rng.uniform(ilower, iupper)
                power = 1 - z - current
                coefficients.update({f"{prefix}_Z": z, f"{prefix}_I": current,
                                     f"{prefix}_P": power})
            mapping = database["powerfactory"]["zip_model"]
            item.update({
                "model": "balanced voltage-dependent ZIP load (load flow only)",
                "zip_coefficients": coefficients,
                "type_attributes": {
                    **mapping["exponents"],
                    **{attribute: coefficients[source]
                       for source, attribute in mapping["writable_coefficients"].items()},
                },
                "derived_type_attributes": {
                    attribute: coefficients[source]
                    for source, attribute in mapping["derived_coefficients"].items()
                },
                "sampling_method": "sequential uniform feasible Z and conditional I; P = 1 - Z - I",
                "limitations": [
                    "Enable Consider Voltage Dependency of Loads in ComLdf to apply ZIP behavior.",
                    "No load-flow command settings are changed by this creator.",
                    "RMS and EMT ZIP behavior have not been validated.",
                ],
            })
        return class_name, item

    @classmethod
    def list_evemtbench_transformer_profiles(
        cls,
        voltage_class: str = "",
        rated_power_mva: Optional[float] = None,
    ) -> dict[str, Any]:
        """List the executable transformer catalog without opening PowerFactory."""
        try:
            database = cls._load_evemtbench_database()
            requested_class = str(voltage_class or "").strip()
            classes = database["classes"]
            if requested_class and requested_class not in classes:
                return {
                    "success": False,
                    "message": "voltage_class must be one of: "
                    + ", ".join(classes),
                }

            if rated_power_mva is not None:
                if not requested_class:
                    return {
                        "success": False,
                        "message": (
                            "voltage_class is required when rated_power_mva "
                            "is provided"
                        ),
                    }
                if isinstance(rated_power_mva, bool):
                    return {
                        "success": False,
                        "message": "rated_power_mva must be a number",
                    }
                requested_rating = float(rated_power_mva)
            else:
                requested_rating = None

            selected = (
                {requested_class: classes[requested_class]}
                if requested_class
                else classes
            )
            results = []
            for class_name, transformer_class in selected.items():
                ratings = transformer_class["ratings"]
                if requested_rating is not None:
                    ratings = [
                        rating
                        for rating in ratings
                        if math.isclose(
                            float(rating["rated_power_mva"]),
                            requested_rating,
                        )
                    ]
                    if not ratings:
                        available = ", ".join(
                            str(item["rated_power_mva"])
                            for item in transformer_class["ratings"]
                        )
                        return {
                            "success": False,
                            "message": (
                                "rated_power_mva must be one of: " + available
                            ),
                        }
                results.append({
                    "voltage_class": class_name,
                    "high_voltage_kv": transformer_class["high_voltage_kv"],
                    "low_voltage_kv": transformer_class["low_voltage_kv"],
                    "ratings": ratings,
                    "zero_sequence_rules": transformer_class[
                        "zero_sequence_rules"
                    ],
                })
            return {
                "success": True,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "component_type": "two_winding_transformer",
                "nominal_frequencies_hz": database["sampling"][
                    "nominal_frequencies_hz"
                ],
                "returned_count": len(results),
                "results": results,
                "vector_groups": database["vector_groups"],
                "saturation": database["saturation"],
                "unmapped_source_tables": database["powerfactory"][
                    "unmapped_source_tables"
                ],
                "catalog_only": database["catalog_only"],
            }
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    @classmethod
    def _evemtbench_transformer_plan(
        cls,
        voltage_class: str,
        rated_power_mva: float,
        nominal_frequency_hz: float,
        vector_group: str,
        clock_number: int,
        type_name: str,
        seed: int,
    ):
        database = cls._load_evemtbench_database()
        source = database["classes"][voltage_class]
        rng = random.Random(seed)

        def sampled(value):
            if "value" in value:
                return float(value["value"])
            return round(rng.uniform(float(value["min"]), float(value["max"])), 6)

        rating = next(
            (
                item
                for item in source["ratings"]
                if math.isclose(
                    float(item["rated_power_mva"]),
                    rated_power_mva,
                )
            ),
            None,
        )
        if rating is None:
            available = ", ".join(
                str(item["rated_power_mva"])
                for item in source["ratings"]
            )
            raise RuntimeError(
                f"rated_power_mva must be one of: {available}"
            )
        if vector_group not in rating["vector_groups"]:
            raise RuntimeError(
                "vector_group must be one of: "
                + ", ".join(rating["vector_groups"])
            )
        vector = database["vector_groups"][vector_group]
        # A blank TypTr2 needs its technology and frequency before its
        # impedance fields become usable.
        attributes = {
            "nt2ph": 3,
            "frnom": nominal_frequency_hz,
            "itrmt": 0,
            "itrdr": 0.5,
            "itrdl": 0.5,
            "it0mt": 0,
            "tr2cn_h": vector["high_winding_connection"],
            "tr2cn_l": vector["low_winding_connection"],
            "nt2ag": clock_number,
            "strn": float(rating["rated_power_mva"]),
            "utrn_h": float(source["high_voltage_kv"]),
            "utrn_l": float(source["low_voltage_kv"]),
            "uktr": sampled(rating["short_circuit_voltage_pct"]),
            "pcutr": sampled(rating["winding_losses_kw"]),
            "pfe": sampled(rating["no_load_losses_kw"]),
            "curmg": sampled(rating["no_load_current_pct"]),
        }
        return {
            "name": type_name,
            "catalog_id": database["catalog_id"],
            "source_tables": database["source"]["tables"],
            "published_vector_groups": rating["vector_groups"],
            "selected_vector_group": vector_group,
            "clock_number": clock_number,
            "clock_numbers_referenced_in_text": vector[
                "clock_numbers_referenced_in_text"
            ],
            "parameters": {
                "rated_power_mva": attributes["strn"],
                "nominal_frequency_hz": attributes["frnom"],
                "high_voltage_kv": attributes["utrn_h"],
                "low_voltage_kv": attributes["utrn_l"],
                "short_circuit_voltage_pct": attributes["uktr"],
                "winding_losses_kw": attributes["pcutr"],
                "no_load_losses_kw": attributes["pfe"],
                "no_load_current_pct": attributes["curmg"],
            },
            "powerfactory_attributes": attributes,
            "unmapped_source_tables": database["powerfactory"][
                "unmapped_source_tables"
            ],
        }

    @classmethod
    def create_evemtbench_component(
        cls,
        component_type: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Route one component request to its validated EvEMTBench creator."""
        creators = cls._evemtbench_creators
        kind = str(component_type or "").strip().lower().replace("-", "_")
        method_name = creators.get(kind)
        supported = ", ".join(creators)
        if method_name is None:
            return {
                "success": False,
                "applied": False,
                "component_type": kind,
                "message": f"component_type must be one of: {supported}",
            }
        if not isinstance(parameters, dict):
            return {
                "success": False,
                "applied": False,
                "component_type": kind,
                "message": "parameters must be an object",
            }

        options = dict(parameters)
        private = sorted(
            str(name) for name in options if str(name).startswith("_")
        )
        if private:
            return {
                "success": False,
                "applied": False,
                "component_type": kind,
                "message": (
                    "parameters must not contain private options: "
                    + ", ".join(private)
                ),
            }

        creator = getattr(cls, method_name)
        try:
            inspect.signature(creator).bind(**options)
        except TypeError as exc:
            return {
                "success": False,
                "applied": False,
                "component_type": kind,
                "message": f"Invalid {kind} parameters: {exc}",
            }

        result = dict(creator(**options))
        result["component_type"] = kind
        return result

    @classmethod
    def create_evemtbench_transformer(
        cls,
        voltage_class: str,
        rated_power_mva: float,
        nominal_frequency_hz: float,
        vector_group: str,
        clock_number: int,
        transformer_name: str,
        type_name: str,
        high_voltage_bus_name: str,
        low_voltage_bus_name: str,
        grid_name: str = "",
        seed: int = 0,
        out_of_service: bool = False,
        confirmation: str = "",
        open_digsilent: bool = True,
    ) -> dict[str, Any]:
        """Preview or create a new database-backed TypTr2 and ElmTr2."""
        voltage_class = str(voltage_class or "").strip()
        vector_group = str(vector_group or "").strip()
        transformer_name = str(transformer_name or "").strip()
        type_name = str(type_name or "").strip()
        high_bus_name = str(high_voltage_bus_name or "").strip()
        low_bus_name = str(low_voltage_bus_name or "").strip()
        created_type = None
        created_type_folder = None
        equipment_folder = None
        type_folder = None

        def failure(message, **extra):
            result = {
                "success": False,
                "applied": False,
                "type_created": False,
                "transformer_created": False,
                "message": message,
            }
            result.update(extra)
            return result

        for field_name, value in (
            ("out_of_service", out_of_service),
            ("open_digsilent", open_digsilent),
        ):
            if not isinstance(value, bool):
                return failure(f"{field_name} must be a boolean")

        try:
            database = cls._load_evemtbench_database()
        except Exception as exc:
            return failure(str(exc))
        if voltage_class not in database["classes"]:
            return failure(
                "voltage_class must be one of: "
                + ", ".join(database["classes"])
            )
        for field_name, value in (
            ("transformer_name", transformer_name),
            ("type_name", type_name),
            ("high_voltage_bus_name", high_bus_name),
            ("low_voltage_bus_name", low_bus_name),
        ):
            if not value:
                return failure(f"{field_name} must not be empty")
        for field_name, value in (
            ("transformer_name", transformer_name),
            ("type_name", type_name),
        ):
            if len(value) > cls._max_loc_name_length:
                return failure(
                    f"{field_name} must be at most "
                    f"{cls._max_loc_name_length} characters"
                )
        if high_bus_name.casefold() == low_bus_name.casefold():
            return failure("Transformer buses must be different")
        if isinstance(rated_power_mva, bool):
            return failure("rated_power_mva must be a number")
        try:
            rated_power = float(rated_power_mva)
        except (TypeError, ValueError):
            return failure("rated_power_mva must be a number")
        if not math.isfinite(rated_power) or rated_power <= 0:
            return failure("rated_power_mva must be a finite positive number")
        if isinstance(nominal_frequency_hz, bool):
            return failure("nominal_frequency_hz must be 50 or 60")
        try:
            nominal_frequency = float(nominal_frequency_hz)
        except (TypeError, ValueError):
            return failure("nominal_frequency_hz must be 50 or 60")
        available_frequencies = database["sampling"][
            "nominal_frequencies_hz"
        ]
        if nominal_frequency not in available_frequencies:
            return failure("nominal_frequency_hz must be 50 or 60")
        if (
            isinstance(clock_number, bool)
            or not isinstance(clock_number, int)
            or not 0 <= clock_number <= 11
        ):
            return failure("clock_number must be an integer from 0 to 11")
        if isinstance(seed, bool) or not isinstance(seed, int):
            return failure("seed must be an integer")

        try:
            item = cls._evemtbench_transformer_plan(
                voltage_class,
                rated_power,
                nominal_frequency,
                vector_group,
                clock_number,
                type_name,
                seed,
            )
        except Exception as exc:
            return failure(str(exc))

        confirmation_prefix = (
            f"CREATE {transformer_name} WITH {type_name} {voltage_class} "
            f"{rated_power:g}MVA {vector_group}{clock_number} "
            f"{nominal_frequency:g}Hz seed={seed} "
            f"grid={grid_name or '<active>'} "
            f"buses={high_voltage_bus_name}->{low_voltage_bus_name} "
            f"out_of_service={int(bool(out_of_service))}"
        )

        try:
            app = cls._get_application(open_digsilent)
            if app.GetActiveProject() is None:
                raise RuntimeError("No PowerFactory project is active")

            equipment_folder = app.GetProjectFolder("equip")
            if equipment_folder is None:
                raise RuntimeError(
                    "Equipment Type Library is unavailable: "
                    "GetProjectFolder('equip') returned None"
                )

            type_folders = cls._find_named_contents(
                equipment_folder,
                "Transformer Types",
                "IntPrjfolder",
            )
            if len(type_folders) > 1:
                raise RuntimeError(
                    "Multiple Transformer Types folders were found"
                )
            type_folder = type_folders[0] if type_folders else None

            if cls._find_named_contents(
                equipment_folder,
                type_name,
                "TypTr2",
            ):
                raise RuntimeError(
                    f"Transformer type already exists: {type_name}"
                )

            grid = cls._select_grid(app, grid_name)
            if cls._find_named_contents(
                grid,
                transformer_name,
                "ElmTr2",
            ):
                raise RuntimeError(
                    f"Transformer already exists in the selected grid: "
                    f"{transformer_name}"
                )
            high_bus = cls._select_bus(grid, high_bus_name)
            low_bus = cls._select_bus(grid, low_bus_name)
            transformer_class = database["classes"][voltage_class]
            for label, bus, expected in (
                (
                    "high-voltage",
                    high_bus,
                    float(transformer_class["high_voltage_kv"]),
                ),
                (
                    "low-voltage",
                    low_bus,
                    float(transformer_class["low_voltage_kv"]),
                ),
            ):
                actual = float(bus.GetAttribute("uknom"))
                if not math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-6):
                    raise RuntimeError(
                        f"{label} bus nominal voltage is {actual:g} kV; "
                        f"expected {expected:g} kV for {voltage_class}"
                    )

            required_confirmation = cls._creation_confirmation_token(
                confirmation_prefix,
                {
                    "component": "transformer",
                    "catalog_id": database["catalog_id"],
                    "resolved_item": item,
                    "voltage_class": voltage_class,
                    "rated_power_mva": rated_power,
                    "nominal_frequency_hz": nominal_frequency,
                    "vector_group": vector_group,
                    "clock_number": clock_number,
                    "transformer_name": transformer_name,
                    "type_name": type_name,
                    "high_voltage_bus_name": high_bus_name,
                    "low_voltage_bus_name": low_bus_name,
                    "requested_grid_name": str(grid_name or "").strip(),
                    "resolved_grid": grid.GetFullName(),
                    "resolved_high_voltage_bus": high_bus.GetFullName(),
                    "resolved_low_voltage_bus": low_bus.GetFullName(),
                    "seed": seed,
                    "out_of_service": bool(out_of_service),
                },
            )

            result = {
                "success": True,
                "applied": False,
                "type_created": False,
                "transformer_created": False,
                "voltage_class": voltage_class,
                "seed": seed,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "target": {
                    "grid": grid.GetFullName(),
                    "transformer_name": transformer_name,
                    "type_name": type_name,
                    "high_voltage_bus": high_bus.GetFullName(),
                    "low_voltage_bus": low_bus.GetFullName(),
                    "out_of_service": bool(out_of_service),
                },
                "equipment_folder": (
                    type_folder or equipment_folder
                ).GetFullName(),
                "item": item,
                "confirmation_required": required_confirmation,
                "message": (
                    "Preview only; no transformer type, grid element, cubicle, "
                    "or switch was created. Tables 10 and 12 are present in "
                    "the database but remain unmapped to PowerFactory."
                ),
            }
            if not confirmation:
                return result
            if confirmation != required_confirmation:
                return failure(
                    f"confirmation must exactly match: {required_confirmation}",
                    item=item,
                )

            if type_folder is None:
                type_folder = equipment_folder.CreateObject(
                    "IntPrjfolder",
                    "Transformer Types",
                )
                if type_folder is None:
                    raise RuntimeError(
                        "Could not create Transformer Types folder"
                    )
                created_type_folder = type_folder

            created_type = type_folder.CreateObject("TypTr2", type_name)
            if created_type is None:
                raise RuntimeError(
                    f"Could not create transformer type: {type_name}"
                )
            if created_type.GetClassName() != "TypTr2":
                raise RuntimeError("PowerFactory created an unexpected type class")
            attributes = item["powerfactory_attributes"]
            structural_names = {
                "nt2ph",
                "frnom",
                "itrmt",
                "itrdr",
                "itrdl",
                "it0mt",
                "tr2cn_h",
                "tr2cn_l",
                "nt2ag",
            }
            structural = {
                name: value
                for name, value in attributes.items()
                if name in structural_names
            }
            electrical = {
                name: value
                for name, value in attributes.items()
                if name not in structural_names
            }
            nameplate = {
                name: electrical.pop(name)
                for name in ("strn", "utrn_h", "utrn_l")
            }
            resistance_pu = electrical["pcutr"] / (
                nameplate["strn"] * 1000.0
            )
            impedance_pu = electrical["uktr"] / 100.0
            if resistance_pu > impedance_pu:
                raise RuntimeError(
                    "Transformer copper losses exceed the sampled "
                    "short-circuit impedance"
                )
            performance = {
                "r1pu": resistance_pu,
                "x1pu": math.sqrt(
                    max(0.0, impedance_pu**2 - resistance_pu**2)
                ),
                "pfe": electrical["pfe"],
                "curmg": electrical["curmg"],
            }

            def commit_type_attributes(values, stage, direct=False):
                if direct:
                    for name, value in values.items():
                        setattr(created_type, name, value)
                        cls._verify_attributes(
                            created_type,
                            {name: value},
                            "Transformer type",
                            "immediately after direct assignment",
                        )
                else:
                    cls._set_and_verify_attributes(
                        created_type,
                        values,
                        "Transformer type",
                    )
                created_type.WriteChangesToDb()
                cls._verify_attributes(
                    created_type,
                    values,
                    "Transformer type",
                    f"after committing {stage} attributes",
                )

            commit_type_attributes(structural, "structural")
            commit_type_attributes(nameplate, "nameplate")
            commit_type_attributes(performance, "performance", direct=True)
            cls._verify_attributes(
                created_type,
                {
                    name: electrical[name]
                    for name in ("pcutr", "uktr", "pfe", "curmg")
                },
                "Transformer type",
                "after deriving source performance values",
            )
            cls._verify_attributes(
                created_type,
                attributes,
                "Transformer type",
                "after completing transformer type initialization",
            )
            if str(created_type.GetAttribute("loc_name")) != type_name:
                raise RuntimeError(
                    f"PowerFactory did not retain type name: {type_name}"
                )
            item["full_name"] = created_type.GetFullName()

            _, _, created_transformer, _ = cls._create_connected_element(
                app,
                "ElmTr2",
                "Transformer",
                transformer_name,
                (high_bus_name, low_bus_name),
                grid_name,
                attributes={
                    "typ_id": created_type,
                    "outserv": int(bool(out_of_service)),
                },
                connection_attributes=("bushv", "buslv"),
            )

            result.update({
                "applied": True,
                "type_created": True,
                "transformer_created": True,
                "created_type": created_type.GetFullName(),
                "created_transformer": created_transformer.GetFullName(),
                "message": (
                    f"Created TypTr2 '{type_name}' and connected ElmTr2 "
                    f"'{transformer_name}'"
                ),
            })
            return result

        except Exception as exc:
            return failure(
                str(exc),
                **cls._rollback_equipment_type(
                    equipment_folder, created_type, created_type_folder,
                    type_name, "TypTr2", "Transformer Types",
                ),
                item=item,
            )

    @classmethod
    def create_evemtbench_line(
        cls,
        voltage_kv: float,
        nominal_frequency_hz: float,
        rated_current_ka: float,
        profile: str,
        length_km: float,
        line_name: str,
        type_name: str,
        bus1_name: str,
        bus2_name: str,
        grid_name: str = "",
        out_of_service: bool = False,
        confirmation: str = "",
        open_digsilent: bool = True,
        _database_loader=None,
        _plan_builder=None,
        _component_label: str = "overhead lines",
        _preview_message: str = "",
    ) -> dict[str, Any]:
        """Preview or create a new EvEMTBench TypLne and connected ElmLne."""
        profile = str(profile or "").strip().lower()
        line_name = str(line_name or "").strip()
        type_name = str(type_name or "").strip()
        first_bus_name = str(bus1_name or "").strip()
        second_bus_name = str(bus2_name or "").strip()
        created_type = None
        created_type_folder = None
        equipment_folder = None
        type_folder = None
        item = None

        def failure(message, **extra):
            result = {
                "success": False,
                "applied": False,
                "type_created": False,
                "line_created": False,
                "message": message,
            }
            result.update(extra)
            return result

        for field_name, value in (
            ("out_of_service", out_of_service),
            ("open_digsilent", open_digsilent),
        ):
            if not isinstance(value, bool):
                return failure(f"{field_name} must be a boolean")

        database_loader = _database_loader or cls._load_evemtbench_line_database
        plan_builder = _plan_builder or cls._evemtbench_line_plan
        try:
            database = database_loader()
        except Exception as exc:
            return failure(str(exc))
        for field_name, value in (
            ("line_name", line_name),
            ("type_name", type_name),
            ("bus1_name", first_bus_name),
            ("bus2_name", second_bus_name),
        ):
            if not value:
                return failure(f"{field_name} must not be empty")
        for field_name, value in (
            ("line_name", line_name),
            ("type_name", type_name),
        ):
            if len(value) > cls._max_loc_name_length:
                return failure(
                    f"{field_name} must be at most "
                    f"{cls._max_loc_name_length} characters"
                )
        if first_bus_name.casefold() == second_bus_name.casefold():
            return failure("Line buses must be different")

        def positive_number(name, value):
            if isinstance(value, bool):
                raise ValueError(f"{name} must be a number")
            try:
                converted = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{name} must be a number") from exc
            if not math.isfinite(converted) or converted <= 0:
                raise ValueError(f"{name} must be a finite positive number")
            return converted

        try:
            voltage = positive_number("voltage_kv", voltage_kv)
            nominal_frequency = positive_number(
                "nominal_frequency_hz",
                nominal_frequency_hz,
            )
            rated_current = positive_number(
                "rated_current_ka",
                rated_current_ka,
            )
            line_length = positive_number("length_km", length_km)
        except ValueError as exc:
            return failure(str(exc))
        if nominal_frequency not in database["nominal_frequencies_hz"]:
            return failure("nominal_frequency_hz must be 50 or 60")

        try:
            voltage_class, line_class, item = plan_builder(
                voltage,
                nominal_frequency,
                rated_current,
                profile,
                type_name,
            )
        except Exception as exc:
            return failure(str(exc))
        length_range = line_class["length_km"]
        if not (
            float(length_range["min"])
            <= line_length
            <= float(length_range["max"])
        ):
            return failure(
                f"length_km must be between {length_range['min']:g} and "
                f"{length_range['max']:g} for {voltage_class} kV "
                f"{_component_label}",
                item=item,
            )
        current_guidance = line_class.get("rated_current_guidance_ka")
        if current_guidance and not (
            float(current_guidance["min"])
            <= rated_current
            <= float(current_guidance["max"])
        ):
            return failure(
                f"rated_current_ka must be between "
                f"{current_guidance['min']:g} and "
                f"{current_guidance['max']:g} for {voltage_class} kV "
                "overhead lines",
                item=item,
            )

        confirmation_prefix = (
            f"CREATE {line_name} WITH {type_name} {voltage_class}kV "
            f"{profile} {line_length:g}km {rated_current:g}kA "
            f"{nominal_frequency:g}Hz grid={grid_name or '<active>'} "
            f"buses={bus1_name}->{bus2_name} "
            f"out_of_service={int(bool(out_of_service))}"
        )

        try:
            app = cls._get_application(open_digsilent)
            if app.GetActiveProject() is None:
                raise RuntimeError("No PowerFactory project is active")

            equipment_folder = app.GetProjectFolder("equip")
            if equipment_folder is None:
                raise RuntimeError(
                    "Equipment Type Library is unavailable: "
                    "GetProjectFolder('equip') returned None"
                )
            type_folders = cls._find_named_contents(
                equipment_folder,
                "Line Types",
                "IntPrjfolder",
            )
            if len(type_folders) > 1:
                raise RuntimeError("Multiple Line Types folders were found")
            type_folder = type_folders[0] if type_folders else None
            if cls._find_named_contents(equipment_folder, type_name, "TypLne"):
                raise RuntimeError(f"Line type already exists: {type_name}")

            grid = cls._select_grid(app, grid_name)
            if cls._find_named_contents(grid, line_name, "ElmLne"):
                raise RuntimeError(
                    f"Line already exists in the selected grid: {line_name}"
                )
            first_bus = cls._select_bus(grid, first_bus_name)
            second_bus = cls._select_bus(grid, second_bus_name)
            for label, bus in (("first", first_bus), ("second", second_bus)):
                actual = float(bus.GetAttribute("uknom"))
                if not math.isclose(actual, voltage, rel_tol=1e-9, abs_tol=1e-6):
                    raise RuntimeError(
                        f"{label} bus nominal voltage is {actual:g} kV; "
                        f"expected {voltage_class} kV"
                    )

            required_confirmation = cls._creation_confirmation_token(
                confirmation_prefix,
                {
                    "component": _component_label,
                    "catalog_id": database["catalog_id"],
                    "resolved_item": item,
                    "line_name": line_name,
                    "type_name": type_name,
                    "voltage_kv": voltage,
                    "nominal_frequency_hz": nominal_frequency,
                    "rated_current_ka": rated_current,
                    "profile": profile,
                    "length_km": line_length,
                    "requested_bus1_name": first_bus_name,
                    "requested_bus2_name": second_bus_name,
                    "requested_grid_name": str(grid_name or "").strip(),
                    "resolved_grid": grid.GetFullName(),
                    "resolved_bus1": first_bus.GetFullName(),
                    "resolved_bus2": second_bus.GetFullName(),
                    "out_of_service": bool(out_of_service),
                },
            )

            result = {
                "success": True,
                "applied": False,
                "type_created": False,
                "line_created": False,
                "voltage_class": voltage_class,
                "profile": profile,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "target": {
                    "grid": grid.GetFullName(),
                    "line_name": line_name,
                    "type_name": type_name,
                    "bus1": first_bus.GetFullName(),
                    "bus2": second_bus.GetFullName(),
                    "length_km": line_length,
                    "out_of_service": bool(out_of_service),
                },
                "equipment_folder": (
                    type_folder or equipment_folder
                ).GetFullName(),
                "item": item,
                "confirmation_required": required_confirmation,
                "message": (
                    _preview_message
                    or "Preview only; no line type, grid element, cubicle, or "
                    "switch was created. The profile uses the paper's "
                    "published sequence-parameter percentile, not a geometric "
                    "ULM model."
                ),
            }
            if not confirmation:
                return result
            if confirmation != required_confirmation:
                return failure(
                    f"confirmation must exactly match: {required_confirmation}",
                    item=item,
                )

            if type_folder is None:
                type_folder = equipment_folder.CreateObject(
                    "IntPrjfolder",
                    "Line Types",
                )
                if type_folder is None:
                    raise RuntimeError("Could not create Line Types folder")
                created_type_folder = type_folder

            created_type = type_folder.CreateObject("TypLne", type_name)
            if created_type is None:
                raise RuntimeError(f"Could not create line type: {type_name}")
            if created_type.GetClassName() != "TypLne":
                raise RuntimeError("PowerFactory created an unexpected type class")
            attributes = item["powerfactory_attributes"]
            nameplate = {
                name: attributes[name]
                for name in ("uline", "sline", "frnom")
            }
            electrical = {
                name: value
                for name, value in attributes.items()
                if name not in nameplate
            }
            cls._set_and_verify_attributes(
                created_type,
                nameplate,
                "Line type",
            )
            created_type.WriteChangesToDb()
            cls._verify_attributes(
                created_type,
                nameplate,
                "Line type",
                "after committing nameplate attributes",
            )
            cls._set_and_verify_attributes(
                created_type,
                electrical,
                "Line type",
            )
            created_type.WriteChangesToDb()
            cls._verify_attributes(
                created_type,
                attributes,
                "Line type",
                "after completing line type initialization",
            )
            if str(created_type.GetAttribute("loc_name")) != type_name:
                raise RuntimeError(
                    f"PowerFactory did not retain type name: {type_name}"
                )
            item["full_name"] = created_type.GetFullName()

            _, _, created_line, _ = cls._create_connected_element(
                app,
                "ElmLne",
                "Line",
                line_name,
                (first_bus_name, second_bus_name),
                grid_name,
                attributes={
                    "typ_id": created_type,
                    "dline": line_length,
                    "outserv": int(bool(out_of_service)),
                },
                connection_attributes=("bus1", "bus2"),
            )
            result.update({
                "applied": True,
                "type_created": True,
                "line_created": True,
                "created_type": created_type.GetFullName(),
                "created_line": created_line.GetFullName(),
                "message": (
                    f"Created TypLne '{type_name}' and connected ElmLne "
                    f"'{line_name}'"
                ),
            })
            return result

        except Exception as exc:
            return failure(
                str(exc),
                **cls._rollback_equipment_type(
                    equipment_folder, created_type, created_type_folder,
                    type_name, "TypLne", "Line Types",
                ),
                item=item,
            )

    @classmethod
    def create_evemtbench_cable(
        cls,
        nominal_frequency_hz: float,
        rated_current_ka: float,
        profile: str,
        length_km: float,
        cable_name: str,
        type_name: str,
        bus1_name: str,
        bus2_name: str,
        grid_name: str = "",
        out_of_service: bool = False,
        confirmation: str = "",
        open_digsilent: bool = True,
    ) -> dict[str, Any]:
        """Preview or create a Table 6 cable sequence equivalent."""
        result = cls.create_evemtbench_line(
            20.0,
            nominal_frequency_hz,
            rated_current_ka,
            profile,
            length_km,
            cable_name,
            type_name,
            bus1_name,
            bus2_name,
            grid_name,
            out_of_service,
            confirmation,
            open_digsilent,
            _database_loader=cls._load_evemtbench_cable_database,
            _plan_builder=cls._evemtbench_cable_plan,
            _component_label="underground cables",
            _preview_message=(
                "Preview only; no cable type, grid element, cubicle, or "
                "switch was created. The TypLne uses the paper's published "
                "sequence-parameter percentile, not its geometric ULM model."
            ),
        )
        result["cable_created"] = result.pop("line_created", False)
        if "created_line" in result:
            result["created_cable"] = result.pop("created_line")
        target = result.get("target")
        if isinstance(target, dict) and "line_name" in target:
            target["cable_name"] = target.pop("line_name")
        if result.get("success") and result.get("applied"):
            result["message"] = (
                f"Created TypLne '{type_name}' and connected cable ElmLne "
                f"'{str(cable_name).strip()}'"
            )
        return result

    @classmethod
    def create_evemtbench_external_grid(
        cls,
        voltage_kv: float,
        external_grid_name: str,
        bus_name: str,
        grid_name: str = "",
        seed: int = 0,
        out_of_service: bool = False,
        confirmation: str = "",
        open_digsilent: bool = True,
    ) -> dict[str, Any]:
        """Preview or create a new Table 4 ElmXnet on an existing bus."""
        external_grid_name = str(external_grid_name or "").strip()
        bus_name = str(bus_name or "").strip()

        def failure(message, **extra):
            result = {
                "success": False,
                "applied": False,
                "external_grid_created": False,
                "message": message,
            }
            result.update(extra)
            return result

        for field_name, value in (
            ("out_of_service", out_of_service),
            ("open_digsilent", open_digsilent),
        ):
            if not isinstance(value, bool):
                return failure(f"{field_name} must be a boolean")

        for field_name, value in (
            ("external_grid_name", external_grid_name),
            ("bus_name", bus_name),
        ):
            if not value:
                return failure(f"{field_name} must not be empty")
        if len(external_grid_name) > cls._max_loc_name_length:
            return failure(
                "external_grid_name must be at most "
                f"{cls._max_loc_name_length} characters"
            )
        if isinstance(voltage_kv, bool):
            return failure("voltage_kv must be a number")
        try:
            voltage = float(voltage_kv)
        except (TypeError, ValueError):
            return failure("voltage_kv must be a number")
        if not math.isfinite(voltage) or voltage <= 0:
            return failure("voltage_kv must be a finite positive number")
        if isinstance(seed, bool) or not isinstance(seed, int):
            return failure("seed must be an integer")

        try:
            database = cls._load_evemtbench_external_grid_database()
            voltage_class, item = cls._evemtbench_external_grid_plan(
                voltage,
                external_grid_name,
                seed,
            )
        except Exception as exc:
            return failure(str(exc))

        confirmation_prefix = (
            f"CREATE {external_grid_name} AT {bus_name} "
            f"{voltage:g}kV seed={seed} grid={grid_name or '<active>'} "
            f"out_of_service={int(bool(out_of_service))}"
        )
        creating = False
        try:
            app = cls._get_application(open_digsilent)
            if app.GetActiveProject() is None:
                raise RuntimeError("No PowerFactory project is active")
            grid = cls._select_grid(app, grid_name)
            if cls._find_named_contents(
                grid,
                external_grid_name,
                "ElmXnet",
            ):
                raise RuntimeError(
                    "External grid already exists in the selected grid: "
                    f"{external_grid_name}"
                )
            bus = cls._select_bus(grid, bus_name)
            actual_voltage = float(bus.GetAttribute("uknom"))
            if not math.isclose(
                actual_voltage,
                voltage,
                rel_tol=1e-9,
                abs_tol=1e-6,
            ):
                raise RuntimeError(
                    f"Bus nominal voltage is {actual_voltage:g} kV; "
                    f"expected {voltage:g} kV"
                )

            required_confirmation = cls._creation_confirmation_token(
                confirmation_prefix,
                {
                    "component": "external_grid",
                    "catalog_id": database["catalog_id"],
                    "resolved_item": item,
                    "voltage_kv": voltage,
                    "external_grid_name": external_grid_name,
                    "requested_bus_name": bus_name,
                    "requested_grid_name": str(grid_name or "").strip(),
                    "resolved_grid": grid.GetFullName(),
                    "resolved_bus": bus.GetFullName(),
                    "seed": seed,
                    "out_of_service": bool(out_of_service),
                },
            )

            result = {
                "success": True,
                "applied": False,
                "external_grid_created": False,
                "voltage_class": voltage_class,
                "seed": seed,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "target": {
                    "grid": grid.GetFullName(),
                    "external_grid_name": external_grid_name,
                    "bus": bus.GetFullName(),
                    "out_of_service": bool(out_of_service),
                },
                "item": item,
                "confirmation_required": required_confirmation,
                "message": (
                    "Preview only; no external grid, cubicle, or switch was "
                    "created. Table 4 intervals were sampled reproducibly."
                ),
            }
            if not confirmation:
                return result
            if confirmation != required_confirmation:
                return failure(
                    f"confirmation must exactly match: "
                    f"{required_confirmation}",
                    item=item,
                )

            creating = True
            attributes = {
                **item["powerfactory_attributes"],
                "outserv": int(bool(out_of_service)),
            }
            _, _, created, actual = cls._create_connected_element(
                app,
                "ElmXnet",
                "External grid",
                external_grid_name,
                (bus_name,),
                grid_name,
                attributes=attributes,
                connection_attributes=("bus1",),
            )
            result.update({
                "applied": True,
                "external_grid_created": True,
                "created_external_grid": created.GetFullName(),
                "retained_powerfactory_attributes": actual,
                "message": (
                    f"Created ElmXnet '{external_grid_name}' and connected "
                    f"it to '{bus_name}'"
                ),
            })
            return result
        except Exception as exc:
            message = str(exc)
            extra = {"item": item}
            if creating:
                extra["rolled_back"] = "rolled_back=True" in message
            return failure(message, **extra)

    @classmethod
    def create_evemtbench_load(
        cls,
        voltage_kv: float,
        load_name: str,
        bus_name: str,
        grid_name: str = "",
        seed: int = 0,
        out_of_service: bool = False,
        confirmation: str = "",
        open_digsilent: bool = True,
        load_model: str = "constant_power",
        type_name: str = "",
    ) -> dict[str, Any]:
        """Preview or create a seeded Table 5 ElmLod."""
        load_name = str(load_name or "").strip()
        bus_name = str(bus_name or "").strip()
        created_type = created_type_folder = equipment_folder = type_folder = None

        def failure(message, **extra):
            result = {
                "success": False,
                "applied": False,
                "load_created": False,
                "message": message,
            }
            result.update(extra)
            return result

        for field_name, value in (
            ("out_of_service", out_of_service),
            ("open_digsilent", open_digsilent),
        ):
            if not isinstance(value, bool):
                return failure(f"{field_name} must be a boolean")

        if load_model not in ("constant_power", "zip"):
            return failure("load_model must be constant_power or zip")
        if not isinstance(type_name, str):
            return failure("type_name must be a string")
        type_name = type_name.strip()
        if load_model == "zip" and (not type_name or len(type_name) > cls._max_loc_name_length):
            return failure(f"ZIP type_name must contain 1 to {cls._max_loc_name_length} characters")
        if load_model == "constant_power" and type_name:
            return failure("type_name is only supported for load_model=zip")

        for field_name, value in (
            ("load_name", load_name),
            ("bus_name", bus_name),
        ):
            if not value:
                return failure(f"{field_name} must not be empty")
        if len(load_name) > cls._max_loc_name_length:
            return failure(
                "load_name must be at most "
                f"{cls._max_loc_name_length} characters"
            )
        if isinstance(voltage_kv, bool):
            return failure("voltage_kv must be a number")
        try:
            voltage = float(voltage_kv)
        except (TypeError, ValueError):
            return failure("voltage_kv must be a number")
        if not math.isfinite(voltage) or voltage <= 0:
            return failure("voltage_kv must be a finite positive number")
        if isinstance(seed, bool) or not isinstance(seed, int):
            return failure("seed must be an integer")

        try:
            database = cls._load_evemtbench_load_database()
            voltage_class, item = cls._evemtbench_load_plan(
                voltage,
                load_name,
                seed,
                load_model,
            )
        except Exception as exc:
            return failure(str(exc))

        confirmation_prefix = (
            f"CREATE {load_name} AT {bus_name} "
            f"{voltage:g}kV seed={seed} grid={grid_name or '<active>'} "
            f"out_of_service={int(bool(out_of_service))}"
        )
        creating = False
        try:
            app = cls._get_application(open_digsilent)
            if app.GetActiveProject() is None:
                raise RuntimeError("No PowerFactory project is active")
            if load_model == "zip":
                equipment_folder = app.GetProjectFolder("equip")
                if equipment_folder is None:
                    raise RuntimeError("Equipment Type Library is unavailable")
                folders = cls._find_named_contents(equipment_folder, "Load Types", "IntPrjfolder")
                if len(folders) > 1:
                    raise RuntimeError("Multiple Load Types folders were found")
                type_folder = folders[0] if folders else None
                if cls._find_named_contents(equipment_folder, type_name, "TypLod"):
                    raise RuntimeError(f"Load type already exists: {type_name}")
                item["type_destination"] = {
                    "equipment_folder": equipment_folder.GetFullName(),
                    "load_types_folder": type_folder.GetFullName() if type_folder else None,
                    "create_folder": type_folder is None,
                    "type_name": type_name,
                }
            grid = cls._select_grid(app, grid_name)
            if cls._find_named_contents(grid, load_name, "ElmLod"):
                raise RuntimeError(
                    "Load already exists in the selected grid: " + load_name
                )
            bus = cls._select_bus(grid, bus_name)
            actual_voltage = float(bus.GetAttribute("uknom"))
            if not math.isclose(
                actual_voltage,
                voltage,
                rel_tol=1e-9,
                abs_tol=1e-6,
            ):
                raise RuntimeError(
                    f"Bus nominal voltage is {actual_voltage:g} kV; "
                    f"expected {voltage:g} kV"
                )

            required_confirmation = cls._creation_confirmation_token(
                confirmation_prefix,
                {
                    "component": "load",
                    "load_model": load_model,
                    "type_name": type_name,
                    "catalog_id": database["catalog_id"],
                    "resolved_item": item,
                    "voltage_kv": voltage,
                    "load_name": load_name,
                    "requested_bus_name": bus_name,
                    "requested_grid_name": str(grid_name or "").strip(),
                    "resolved_grid": grid.GetFullName(),
                    "resolved_bus": bus.GetFullName(),
                    "seed": seed,
                    "out_of_service": bool(out_of_service),
                },
            )

            result = {
                "success": True,
                "applied": False,
                "load_created": False,
                "type_created": False,
                "load_model": load_model,
                "voltage_class": voltage_class,
                "seed": seed,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "target": {
                    "grid": grid.GetFullName(),
                    "load_name": load_name,
                    "bus": bus.GetFullName(),
                    "out_of_service": bool(out_of_service),
                },
                "item": item,
                "confirmation_required": required_confirmation,
                "message": (
                    "Preview only; no type, load, cubicle, or switch was created. "
                    "Table 5 power intervals were sampled reproducibly."
                ),
            }
            if not confirmation:
                return result
            if confirmation != required_confirmation:
                return failure(
                    "confirmation must exactly match: "
                    + required_confirmation,
                    item=item,
                )

            creating = True
            retained_type = retained_derived = None
            if load_model == "zip":
                if type_folder is None:
                    type_folder = equipment_folder.CreateObject("IntPrjfolder", "Load Types")
                    if type_folder is None:
                        raise RuntimeError("Could not create Load Types folder")
                    created_type_folder = type_folder
                created_type = type_folder.CreateObject("TypLod", type_name)
                if created_type is None:
                    raise RuntimeError(f"Could not create load type: {type_name}")
                if created_type.GetClassName() != "TypLod":
                    raise RuntimeError("PowerFactory created an unexpected type class")
                # Native assignment matches the Lab PC write/readback validation.
                for attribute, value in item["type_attributes"].items():
                    setattr(created_type, attribute, value)
                    cls._verify_attributes(created_type, {attribute: value}, "ZIP load type")
                created_type.WriteChangesToDb()
                retained_type = cls._verify_attributes(
                    created_type, item["type_attributes"], "ZIP load type", "after database write")
                retained_derived = cls._verify_attributes(
                    created_type, item["derived_type_attributes"], "ZIP load type", "derived coefficients")
                if str(created_type.GetAttribute("loc_name")) != type_name:
                    raise RuntimeError("PowerFactory did not retain the load type name")
            attributes = {
                **item["powerfactory_attributes"],
                "outserv": int(bool(out_of_service)),
            }
            if created_type is not None:
                attributes["typ_id"] = created_type
            _, _, created, actual = cls._create_connected_element(
                app,
                "ElmLod",
                "Load",
                load_name,
                (bus_name,),
                grid_name,
                attributes=attributes,
                connection_attributes=("bus1",),
            )
            result.update({
                "applied": True,
                "load_created": True,
                "created_load": created.GetFullName(),
                "retained_powerfactory_attributes": actual,
                "message": (
                    f"Created ElmLod '{load_name}' and connected it to "
                    f"'{bus_name}'"
                ),
            })
            if created_type is not None:
                # Avoid serializing a live PowerFactory DataObject in the response.
                actual["typ_id"] = created_type.GetFullName()
                result.update(type_created=True, created_type=created_type.GetFullName(),
                              retained_type_attributes=retained_type,
                              retained_derived_attributes=retained_derived)
            return result
        except Exception as exc:
            message = str(exc)
            extra = {"item": item}
            if creating:
                extra["rolled_back"] = "rolled_back=True" in message
            if load_model == "zip":
                # Never remove a type still referenced by a failed element rollback.
                survivors = cls._find_named_contents(grid, load_name, "ElmLod") if creating else []
                if survivors:
                    extra.update(rolled_back=False, type_created=created_type is not None,
                                 remaining_type=type_name if created_type is not None else None,
                                 remaining_load=survivors[0].GetFullName())
                else:
                    rollback = cls._rollback_equipment_type(
                        equipment_folder, created_type, created_type_folder,
                        type_name, "TypLod", "Load Types")
                    if rollback["rolled_back"] is None:
                        rollback.pop("rolled_back")
                    extra.update(rollback)
            return failure(message, **extra)

    @classmethod
    def create_evemtbench_synchronous_machine(
        cls,
        machine_type: str,
        rated_power_mva: float,
        machine_name: str,
        type_name: str,
        bus_name: str,
        grid_name: str = "",
        seed: int = 0,
        active_power_mw: float = 0.0,
        reactive_power_mvar: float = 0.0,
        out_of_service: bool = False,
        confirmation: str = "",
        open_digsilent: bool = True,
    ) -> dict[str, Any]:
        """Preview or create a seeded round-rotor TypSym and ElmSym."""
        machine_type = str(machine_type or "").strip().lower()
        machine_name = str(machine_name or "").strip()
        type_name = str(type_name or "").strip()
        bus_name = str(bus_name or "").strip()
        created_type = None
        created_type_folder = None
        equipment_folder = None
        item = None

        def failure(message, **extra):
            result = {
                "success": False,
                "applied": False,
                "type_created": False,
                "machine_created": False,
                "message": message,
            }
            result.update(extra)
            return result

        for field_name, value in (
            ("out_of_service", out_of_service),
            ("open_digsilent", open_digsilent),
        ):
            if not isinstance(value, bool):
                return failure(f"{field_name} must be a boolean")

        for field_name, value in (
            ("machine_name", machine_name),
            ("type_name", type_name),
            ("bus_name", bus_name),
        ):
            if not value:
                return failure(f"{field_name} must not be empty")
        for field_name, value in (
            ("machine_name", machine_name),
            ("type_name", type_name),
        ):
            if len(value) > cls._max_loc_name_length:
                return failure(
                    f"{field_name} must be at most "
                    f"{cls._max_loc_name_length} characters"
                )
        if isinstance(seed, bool) or not isinstance(seed, int):
            return failure("seed must be an integer")

        numbers = {}
        for field_name, value in (
            ("rated_power_mva", rated_power_mva),
            ("active_power_mw", active_power_mw),
            ("reactive_power_mvar", reactive_power_mvar),
        ):
            if isinstance(value, bool):
                return failure(f"{field_name} must be a number")
            try:
                number = float(value)
            except (TypeError, ValueError):
                return failure(f"{field_name} must be a number")
            if not math.isfinite(number):
                return failure(f"{field_name} must be finite")
            numbers[field_name] = number
        rated_power = numbers["rated_power_mva"]
        active_power = numbers["active_power_mw"]
        reactive_power = numbers["reactive_power_mvar"]
        if rated_power <= 0:
            return failure("rated_power_mva must be positive")
        if active_power < 0:
            return failure("active_power_mw must be non-negative")

        try:
            database = cls._load_evemtbench_synchronous_machine_database()
            item = cls._evemtbench_synchronous_machine_plan(
                machine_type,
                rated_power,
                type_name,
                seed,
            )
        except Exception as exc:
            return failure(str(exc))

        source_parameters = item["parameters"]
        if math.hypot(active_power, reactive_power) > rated_power + 1e-9:
            return failure(
                "The requested active/reactive operating point exceeds "
                "rated_power_mva",
                item=item,
            )
        reactive_min = (
            float(source_parameters["reactive_power_min_pu"])
            * rated_power
        )
        reactive_max = (
            float(source_parameters["reactive_power_max_pu"])
            * rated_power
        )
        if not reactive_min <= reactive_power <= reactive_max:
            return failure(
                "reactive_power_mvar must be between "
                f"{reactive_min:g} and {reactive_max:g} for this type",
                item=item,
            )

        rated_voltage = float(source_parameters["rated_voltage_kv"])
        confirmation_prefix = (
            f"CREATE {machine_name} WITH {type_name} {machine_type} "
            f"{rated_power:g}MVA {rated_voltage:g}kV seed={seed} "
            f"grid={grid_name or '<active>'} bus={bus_name} "
            f"p={active_power:g}MW q={reactive_power:g}Mvar "
            f"out_of_service={int(bool(out_of_service))}"
        )
        try:
            app = cls._get_application(open_digsilent)
            if app.GetActiveProject() is None:
                raise RuntimeError("No PowerFactory project is active")

            equipment_folder = app.GetProjectFolder("equip")
            if equipment_folder is None:
                raise RuntimeError(
                    "Equipment Type Library is unavailable: "
                    "GetProjectFolder('equip') returned None"
                )
            type_folders = cls._find_named_contents(
                equipment_folder,
                "Generator Types",
                "IntPrjfolder",
            )
            if len(type_folders) > 1:
                raise RuntimeError("Multiple Generator Types folders were found")
            type_folder = type_folders[0] if type_folders else None
            if cls._find_named_contents(
                equipment_folder,
                type_name,
                "TypSym",
            ):
                raise RuntimeError(
                    f"Synchronous-machine type already exists: {type_name}"
                )

            grid = cls._select_grid(app, grid_name)
            if cls._find_named_contents(grid, machine_name, "ElmSym"):
                raise RuntimeError(
                    "Synchronous machine already exists in the selected "
                    f"grid: {machine_name}"
                )
            bus = cls._select_bus(grid, bus_name)
            actual_voltage = float(bus.GetAttribute("uknom"))
            if not math.isclose(
                actual_voltage,
                rated_voltage,
                rel_tol=1e-9,
                abs_tol=1e-6,
            ):
                raise RuntimeError(
                    f"Bus nominal voltage is {actual_voltage:g} kV; "
                    f"expected {rated_voltage:g} kV for a "
                    f"{rated_power:g} MVA {machine_type} machine"
                )

            required_confirmation = cls._creation_confirmation_token(
                confirmation_prefix,
                {
                    "component": "synchronous_machine",
                    "catalog_id": database["catalog_id"],
                    "resolved_item": item,
                    "machine_type": machine_type,
                    "rated_power_mva": rated_power,
                    "rated_voltage_kv": rated_voltage,
                    "machine_name": machine_name,
                    "type_name": type_name,
                    "requested_bus_name": bus_name,
                    "requested_grid_name": str(grid_name or "").strip(),
                    "resolved_grid": grid.GetFullName(),
                    "resolved_bus": bus.GetFullName(),
                    "seed": seed,
                    "active_power_mw": active_power,
                    "reactive_power_mvar": reactive_power,
                    "out_of_service": bool(out_of_service),
                },
            )

            result = {
                "success": True,
                "applied": False,
                "type_created": False,
                "machine_created": False,
                "machine_type": machine_type,
                "seed": seed,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "target": {
                    "grid": grid.GetFullName(),
                    "machine_name": machine_name,
                    "type_name": type_name,
                    "bus": bus.GetFullName(),
                    "active_power_mw": active_power,
                    "reactive_power_mvar": reactive_power,
                    "out_of_service": bool(out_of_service),
                },
                "equipment_folder": (
                    type_folder or equipment_folder
                ).GetFullName(),
                "item": item,
                "confirmation_required": required_confirmation,
                "message": (
                    "Preview only; no synchronous-machine type, grid "
                    "element, cubicle, or switch was created. Table 13 "
                    "ranges were sampled reproducibly."
                ),
            }
            if not confirmation:
                return result
            if confirmation != required_confirmation:
                return failure(
                    "confirmation must exactly match: "
                    + required_confirmation,
                    item=item,
                )

            if type_folder is None:
                type_folder = equipment_folder.CreateObject(
                    "IntPrjfolder",
                    "Generator Types",
                )
                if type_folder is None:
                    raise RuntimeError("Could not create Generator Types folder")
                created_type_folder = type_folder

            created_type = type_folder.CreateObject("TypSym", type_name)
            if created_type is None:
                raise RuntimeError(
                    f"Could not create synchronous-machine type: {type_name}"
                )
            if created_type.GetClassName() != "TypSym":
                raise RuntimeError("PowerFactory created an unexpected type class")

            attributes = item["powerfactory_attributes"]
            structural = {"iturbo": attributes["iturbo"]}
            nameplate = {
                name: attributes[name]
                for name in ("sgn", "ugn", "cosn")
            }
            electrical = {
                name: value
                for name, value in attributes.items()
                if name not in structural and name not in nameplate
            }
            for values, stage in (
                (structural, "rotor-mode"),
                (nameplate, "nameplate"),
                (electrical, "electrical"),
            ):
                cls._set_and_verify_attributes(
                    created_type,
                    values,
                    "Synchronous-machine type",
                )
                created_type.WriteChangesToDb()
                cls._verify_attributes(
                    created_type,
                    values,
                    "Synchronous-machine type",
                    f"after committing {stage} attributes",
                )
            retained_type_attributes = cls._verify_attributes(
                created_type,
                attributes,
                "Synchronous-machine type",
                "after completing type initialization",
            )
            retained_derived_attributes = cls._verify_attributes(
                created_type,
                item["powerfactory_derived_attributes"],
                "Synchronous-machine type",
                "after deriving short-circuit time constants",
            )
            if str(created_type.GetAttribute("loc_name")) != type_name:
                raise RuntimeError(
                    f"PowerFactory did not retain type name: {type_name}"
                )
            item["full_name"] = created_type.GetFullName()

            _, _, created_machine, retained_element_attributes = (
                cls._create_connected_element(
                    app,
                    "ElmSym",
                    "Synchronous machine",
                    machine_name,
                    (bus_name,),
                    grid_name,
                    attributes={
                        "typ_id": created_type,
                        "pgini": active_power,
                        "qgini": reactive_power,
                        "outserv": int(bool(out_of_service)),
                    },
                    connection_attributes=("bus1",),
                )
            )
            result.update({
                "applied": True,
                "type_created": True,
                "machine_created": True,
                "created_type": created_type.GetFullName(),
                "created_machine": created_machine.GetFullName(),
                "retained_type_attributes": retained_type_attributes,
                "retained_derived_attributes": retained_derived_attributes,
                "retained_element_attributes": retained_element_attributes,
                "message": (
                    f"Created TypSym '{type_name}' and connected ElmSym "
                    f"'{machine_name}'"
                ),
            })
            return result

        except Exception as exc:
            return failure(
                str(exc),
                **cls._rollback_equipment_type(
                    equipment_folder, created_type, created_type_folder,
                    type_name, "TypSym", "Generator Types",
                ),
                item=item,
            )
