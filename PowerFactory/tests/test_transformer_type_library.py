import unittest
from fnmatch import fnmatchcase
from unittest.mock import patch

import Agent_DIgSILENT as agent_module


DEFAULTS = {
    "ElmNet": {"frnom": 0.0},
    "ElmTerm": {"uknom": 0.0, "outserv": 0},
    "StaCubic": {"obj_id": None},
    "StaSwitch": {"aUsage": "", "on_off": 0},
    "ElmTr2": {"typ_id": None, "bushv": None, "buslv": None, "outserv": 0,
               "neutConfig": 1, "cgnd_h": 1, "re0tr_h": 0.0, "xe0tr_h": 0.0},
    "ElmLne": {
        "typ_id": None,
        "bus1": None,
        "bus2": None,
        "dline": 0.0,
        "outserv": 0,
    },
    "ElmXnet": {
        "bus1": None,
        "bustp": "",
        "snss": 0.0,
        "rntxn": 0.0,
        "x0tx1": 0.0,
        "r0tx0": 0.0,
        "usetp": 0.0,
        "phiini": 0.0,
        "outserv": 0,
    },
    "ElmLod": {
        "typ_id": None,
        "bus1": None,
        "plini": 0.0,
        "qlini": 0.0,
        "outserv": 0,
    },
    "ElmSym": {
        "typ_id": None,
        "bus1": None,
        "pgini": 0.0,
        "qgini": 0.0,
        "outserv": 0,
    },
    "TypLod": {
        "aP": 0.0, "bP": 0.0, "aQ": 0.0, "bQ": 0.0,
        "kpu0": 0.0, "kpu1": 1.0, "kpu": 2.0,
        "kqu0": 0.0, "kqu1": 1.0, "kqu": 2.0,
    },
    "TypTr2": {
        "nt2ph": 0,
        "frnom": 0.0,
        "itrmt": 0,
        "itrdr": 0.0,
        "itrdl": 0.0,
        "it0mt": 0,
        "r0pu": 0.0,
        "x0pu": 0.03,
        "uk0tr": 3.0,
        "ur0tr": 0.0,
        "strn": 0.0,
        "utrn_h": 0.0,
        "utrn_l": 0.0,
        "uktr": 0.0,
        "pcutr": 0.0,
        "r1pu": 0.0,
        "x1pu": 0.0,
        "pfe": 0.0,
        "curmg": 0.0,
        "tr2cn_h": "",
        "tr2cn_l": "",
        "nt2ag": 0,
    },
    "TypLne": {
        "uline": 0.0,
        "sline": 0.0,
        "frnom": 0.0,
        "rline": 0.0,
        "xline": 0.0,
        "cline": 0.0,
        "rline0": 0.0,
        "xline0": 0.0,
        "cline0": 0.0,
    },
    "TypSym": {
        "iturbo": 0,
        "sgn": 0.0,
        "ugn": 0.0,
        "cosn": 0.0,
        "rstr": 0.0,
        "xl": 0.0,
        "xd": 0.0,
        "xq": 0.0,
        "xds": 0.0,
        "xqs": 0.0,
        "xdss": 0.0,
        "xqss": 0.0,
        "tds0": 0.0,
        "tqs0": 0.0,
        "tdss0": 0.0,
        "tqss0": 0.0,
        "tds": 0.0,
        "tqs": 0.0,
        "tdss": 0.0,
        "tqss": 0.0,
        "x0sy": 0.0,
        "r0sy": 0.0,
        "x2sy": 0.0,
        "r2sy": 0.0,
        "tag": 0.0,
        "isat": 0,
        "sg10": 0.0,
        "sg12": 0.0,
        "q_max": 0.0,
        "q_min": 0.0,
    },
}


class FakeObject:
    def __setattr__(self, name, value):
        attributes = self.__dict__.get("attributes")
        if attributes is not None and name in attributes:
            if not self._attribute_is_blocked(name):
                attributes[name] = value
                if self.class_name == "TypTr2":
                    if name == "r1pu":
                        attributes["pcutr"] = (
                            value * attributes["strn"] * 1000.0
                        )
                    elif name == "x1pu":
                        attributes["uktr"] = 100.0 * (
                            attributes["r1pu"] ** 2 + value**2
                        ) ** 0.5
                    elif name in ("r0pu", "x0pu"):
                        attributes["ur0tr"] = 100.0 * attributes["r0pu"]
                        attributes["uk0tr"] = 100.0 * (
                            attributes["r0pu"] ** 2 + attributes["x0pu"] ** 2
                        ) ** 0.5
            return
        object.__setattr__(self, name, value)

    def __init__(self, parent, class_name, name):
        self.parent = parent
        self.class_name = class_name
        self.attributes = {"loc_name": name, **DEFAULTS.get(class_name, {})}
        self.objects = {}
        self.reject_attribute = None
        self.reject_set_attribute = None
        self.require_structural_commit = False
        self.require_nameplate_commit = False
        self.require_copper_loss_before_uktr = False
        self.committed_attributes = set()
        self.write_count = 0
        self.delete_fails = False

    def __getitem__(self, class_name):
        return self.objects.setdefault(class_name, [])

    def root(self):
        current = self
        while current.parent is not None:
            current = current.parent
        return current

    def GetAttribute(self, name):
        if self.class_name == "TypLod" and name in ("cP", "cQ"):
            suffix = name[-1]
            return 1.0 - self.attributes["a" + suffix] - self.attributes["b" + suffix]
        return self.attributes[name]

    def _attribute_is_blocked(self, name):
        root = self.root()
        structural = {
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
        nameplate = {"strn", "utrn_h", "utrn_l"}
        return name == root.reject_attribute or (
            name == "uktr"
            and (
                (
                    root.require_structural_commit
                    and not structural <= self.committed_attributes
                )
                or (
                    root.require_nameplate_commit
                    and not nameplate <= self.committed_attributes
                )
                or (
                    root.require_copper_loss_before_uktr
                    and self.attributes["pcutr"] == 0.0
                )
            )
        )

    def SetAttribute(self, name, value):
        if (
            name != self.root().reject_set_attribute
            and not self._attribute_is_blocked(name)
        ):
            self.attributes[name] = value
            if self.class_name == "TypSym":
                derived = {
                    "tds0": ("tds", "xds", "xd"),
                    "tqs0": ("tqs", "xqs", "xq"),
                    "tdss0": ("tdss", "xdss", "xds"),
                    "tqss0": ("tqss", "xqss", "xqs"),
                }.get(name)
                if derived:
                    output, numerator, denominator = derived
                    self.attributes[output] = (
                        value
                        * self.attributes[numerator]
                        / self.attributes[denominator]
                    )
            if name in {"bushv", "buslv", "bus1", "bus2"} and value is not None:
                value.attributes["obj_id"] = self

    def WriteChangesToDb(self):
        self.write_count += 1
        self.committed_attributes.update(self.attributes)

    def GetClassName(self):
        return self.class_name

    def GetFullName(self):
        prefix = self.parent.GetFullName() if self.parent else r"\user"
        return f"{prefix}\\{self.attributes['loc_name']}.{self.class_name}"

    def GetContents(self, query, recursive):
        if query == "*":
            return [item for values in self.objects.values() for item in values]
        name_pattern, class_name = query.rsplit(".", 1)
        matches = [
            item
            for item in self[class_name]
            if fnmatchcase(str(item.GetAttribute("loc_name")), name_pattern)
        ]
        if recursive:
            for values in self.objects.values():
                for item in values:
                    matches.extend(item.GetContents(query, 1))
        return matches

    def CreateObject(self, class_name, name):
        item = FakeObject(self, class_name, name[:40])
        self[class_name].append(item)
        return item

    def Delete(self):
        if self.delete_fails:
            raise RuntimeError("delete failed")
        for attribute in ("bushv", "buslv", "bus1", "bus2"):
            cubicle = self.attributes.get(attribute)
            if cubicle is not None:
                cubicle.attributes["obj_id"] = None
        self.parent[self.class_name].remove(self)

class FakeApplication:
    def __init__(self, equipment_folder, grid):
        self.equipment_folder = equipment_folder
        self.grid = grid
        self.project = FakeObject(None, "IntPrj", "Project")

    def GetActiveProject(self):
        return self.project

    def GetProjectFolder(self, folder_type):
        if folder_type != "equip":
            raise AssertionError(folder_type)
        return self.equipment_folder

    def GetCalcRelevantObjects(self, query):
        if query == "*.ElmNet":
            return [self.grid]
        return []


class EvEMTBenchTransformerTest(unittest.TestCase):
    def network(
        self,
        high_voltage=110.0,
        low_voltage=20.0,
        with_type_folder=True,
    ):
        folder = FakeObject(None, "IntPrjfolder", "Equipment Type Library")
        if with_type_folder:
            folder.CreateObject("IntPrjfolder", "Transformer Types")
        grid = FakeObject(None, "ElmNet", "Grid")
        high_bus = grid.CreateObject("ElmTerm", "HV Bus")
        low_bus = grid.CreateObject("ElmTerm", "LV Bus")
        high_bus.SetAttribute("uknom", high_voltage)
        low_bus.SetAttribute("uknom", low_voltage)
        return folder, grid, high_bus, low_bus, FakeApplication(folder, grid)

    @staticmethod
    def transformer_types(folder):
        type_folders = folder["IntPrjfolder"]
        return type_folders[0]["TypTr2"] if type_folders else []

    def call(self, app, **kwargs):
        arguments = {
            "voltage_class": "110/20",
            "rated_power_mva": 20.0,
            "nominal_frequency_hz": 60.0,
            "vector_group": "YNd",
            "clock_number": 11,
            "transformer_name": "Research Transformer",
            "type_name": "Research Transformer Type",
            "high_voltage_bus_name": "HV Bus",
            "low_voltage_bus_name": "LV Bus",
            "seed": 42,
            "open_digsilent": False,
        }
        arguments.update(kwargs)
        with patch.object(
            agent_module.DIgSILENTAgent,
            "_get_application",
            return_value=app,
        ):
            return agent_module.DIgSILENTAgent.create_evemtbench_transformer(
                **arguments
            )

    def test_database_validates_and_lists_supported_classes(self):
        database = agent_module.DIgSILENTAgent._load_evemtbench_database()
        result = agent_module.DIgSILENTAgent.list_evemtbench_transformer_profiles()

        self.assertEqual(database["schema_version"], 1)
        self.assertTrue(result["success"], result.get("message"))
        self.assertEqual(result["returned_count"], 5)
        self.assertEqual(
            [item["voltage_class"] for item in result["results"]],
            ["20/0.4", "110/20", "110/11", "380/110", "345/25"],
        )
        self.assertEqual(result["unmapped_source_tables"], [10, 12])
        self.assertIn("Institute of Electrical Energy Systems", result["affiliation"])

    def test_catalog_filters_an_exact_rating(self):
        result = agent_module.DIgSILENTAgent.list_evemtbench_transformer_profiles(
            "345/25",
            800.0,
        )

        self.assertTrue(result["success"], result.get("message"))
        self.assertEqual(result["returned_count"], 1)
        self.assertEqual(len(result["results"][0]["ratings"]), 1)
        self.assertEqual(
            result["results"][0]["ratings"][0]["rated_power_mva"],
            800.0,
        )

    def test_preview_is_deterministic_and_creates_nothing(self):
        folder, grid, high_bus, low_bus, app = self.network()

        first = self.call(app)
        second = self.call(app)

        self.assertTrue(first["success"], first.get("message"))
        self.assertFalse(first["applied"])
        self.assertFalse(first["type_created"])
        self.assertFalse(first["transformer_created"])
        self.assertEqual(first["item"], second["item"])
        self.assertEqual(self.transformer_types(folder), [])
        self.assertEqual(grid["ElmTr2"], [])
        self.assertEqual(high_bus["StaCubic"], [])
        self.assertEqual(low_bus["StaCubic"], [])
        self.assertTrue(
            first["confirmation_required"].startswith(
                "CREATE Research Transformer WITH Research Transformer Type "
                "110/20 20MVA YNd11 60Hz seed=42 grid=<active> "
                "buses=HV Bus->LV Bus out_of_service=0"
            )
        )
        self.assertRegex(first["confirmation_required"], r" plan=[0-9a-f]{64}$")
        attributes = first["item"]["powerfactory_attributes"]
        self.assertEqual(
            list(attributes)[:9],
            [
                "nt2ph",
                "frnom",
                "itrmt",
                "itrdr",
                "itrdl",
                "it0mt",
                "tr2cn_h",
                "tr2cn_l",
                "nt2ag",
            ],
        )
        self.assertEqual(attributes["nt2ph"], 3)
        self.assertEqual(attributes["frnom"], 60.0)
        self.assertEqual(attributes["itrmt"], 0)
        self.assertEqual(attributes["itrdr"], 0.5)
        self.assertEqual(attributes["itrdl"], 0.5)
        self.assertEqual(attributes["it0mt"], 0)
        self.assertEqual(attributes["tr2cn_h"], "YN")
        self.assertEqual(attributes["tr2cn_l"], "D")
        self.assertEqual(attributes["nt2ag"], 11)

    def test_confirmation_creates_new_type_and_connected_transformer(self):
        folder, grid, high_bus, low_bus, app = self.network()
        preview = self.call(app, out_of_service=True)

        result = self.call(
            app,
            confirmation=preview["confirmation_required"],
            out_of_service=True,
        )

        self.assertTrue(result["success"], result.get("message"))
        self.assertTrue(result["applied"])
        self.assertTrue(result["type_created"])
        self.assertTrue(result["transformer_created"])
        self.assertEqual(len(self.transformer_types(folder)), 1)
        self.assertEqual(len(grid["ElmTr2"]), 1)
        created_type = self.transformer_types(folder)[0]
        transformer = grid["ElmTr2"][0]
        self.assertIs(transformer.GetAttribute("typ_id"), created_type)
        self.assertEqual(transformer.GetAttribute("outserv"), 1)
        self.assertIs(transformer.GetAttribute("bushv"), high_bus["StaCubic"][0])
        self.assertIs(transformer.GetAttribute("buslv"), low_bus["StaCubic"][0])
        for bus in (high_bus, low_bus):
            cubicle = bus["StaCubic"][0]
            switch = cubicle["StaSwitch"][0]
            self.assertEqual(switch.GetAttribute("aUsage"), "cbk")
            self.assertEqual(switch.GetAttribute("on_off"), 1)
        for attribute, expected in result["item"]["powerfactory_attributes"].items():
            actual = created_type.GetAttribute(attribute)
            if isinstance(expected, float):
                self.assertAlmostEqual(actual, expected)
            else:
                self.assertEqual(actual, expected)
        self.assertAlmostEqual(
            created_type.GetAttribute("r1pu"),
            result["item"]["parameters"]["winding_losses_kw"]
            / (result["item"]["parameters"]["rated_power_mva"] * 1000.0),
        )
        self.assertEqual(created_type.write_count, 3)

    def test_commits_dependencies_before_setting_impedance(self):
        folder, _, _, _, app = self.network()
        folder.require_structural_commit = True
        folder.require_nameplate_commit = True
        folder.require_copper_loss_before_uktr = True
        folder.reject_set_attribute = "pcutr"
        preview = self.call(app)

        result = self.call(app, confirmation=preview["confirmation_required"])

        self.assertTrue(result["success"], result.get("message"))
        self.assertEqual(self.transformer_types(folder)[0].write_count, 3)

    def test_creates_transformer_types_folder_for_greenfield_project(self):
        folder, _, _, _, app = self.network(with_type_folder=False)
        preview = self.call(app)

        result = self.call(app, confirmation=preview["confirmation_required"])

        self.assertTrue(result["success"], result.get("message"))
        self.assertEqual(len(folder["IntPrjfolder"]), 1)
        self.assertEqual(
            folder["IntPrjfolder"][0].GetAttribute("loc_name"),
            "Transformer Types",
        )
        self.assertEqual(len(self.transformer_types(folder)), 1)

    def test_bus_voltage_mismatch_is_rejected_in_preview(self):
        folder, grid, _, _, app = self.network(high_voltage=345.0)

        result = self.call(app)

        self.assertFalse(result["success"])
        self.assertIn("expected 110 kV", result["message"])
        self.assertEqual(self.transformer_types(folder), [])
        self.assertEqual(grid["ElmTr2"], [])

    def test_element_failure_rolls_back_new_type_and_connections(self):
        folder, grid, high_bus, low_bus, app = self.network()
        grid.reject_attribute = "typ_id"
        preview = self.call(app)

        result = self.call(app, confirmation=preview["confirmation_required"])

        self.assertFalse(result["success"])
        self.assertTrue(result["rolled_back"])
        self.assertFalse(result["type_created"])
        self.assertEqual(self.transformer_types(folder), [])
        self.assertEqual(grid["ElmTr2"], [])
        self.assertEqual(high_bus["StaCubic"], [])
        self.assertEqual(low_bus["StaCubic"], [])

    def test_type_attribute_failure_reports_expected_and_actual_values(self):
        folder, grid, high_bus, low_bus, app = self.network()
        folder.reject_attribute = "r1pu"
        preview = self.call(app)

        result = self.call(app, confirmation=preview["confirmation_required"])

        self.assertFalse(result["success"])
        self.assertIn("r1pu", result["message"])
        self.assertIn("got 0.0", result["message"])
        self.assertIn("immediately after direct assignment", result["message"])
        self.assertTrue(result["rolled_back"])
        self.assertEqual(self.transformer_types(folder), [])
        self.assertEqual(grid["ElmTr2"], [])
        self.assertEqual(high_bus["StaCubic"], [])
        self.assertEqual(low_bus["StaCubic"], [])

    def test_failed_type_creation_removes_new_empty_type_folder(self):
        folder, _, _, _, app = self.network(with_type_folder=False)
        folder.reject_attribute = "r1pu"
        preview = self.call(app)

        result = self.call(app, confirmation=preview["confirmation_required"])

        self.assertFalse(result["success"])
        self.assertTrue(result["rolled_back"])
        self.assertEqual(folder["IntPrjfolder"], [])

    def test_failed_type_cleanup_reports_the_surviving_type(self):
        folder, grid, high_bus, low_bus, app = self.network()
        grid.reject_attribute = "typ_id"
        type_folder = folder["IntPrjfolder"][0]
        original_create = type_folder.CreateObject

        def create_type_that_cannot_be_deleted(class_name, name):
            item = original_create(class_name, name)
            item.delete_fails = True
            return item

        type_folder.CreateObject = create_type_that_cannot_be_deleted
        preview = self.call(app)

        result = self.call(app, confirmation=preview["confirmation_required"])

        self.assertFalse(result["success"])
        self.assertFalse(result["rolled_back"])
        self.assertTrue(result["type_created"])
        self.assertEqual(result["remaining_type"], "Research Transformer Type")
        self.assertEqual(len(self.transformer_types(folder)), 1)
        self.assertEqual(grid["ElmTr2"], [])
        self.assertEqual(high_bus["StaCubic"], [])
        self.assertEqual(low_bus["StaCubic"], [])

    def test_rejects_duplicate_invalid_rating_group_and_clock(self):
        folder, _, _, _, app = self.network()
        folder.CreateObject("TypTr2", "Research Transformer Type")

        duplicate = self.call(app)
        bad_rating = self.call(app, rated_power_mva=21.0)
        bad_group = self.call(app, vector_group="YNyn")
        bad_clock = self.call(app, clock_number=12)
        bad_frequency = self.call(app, nominal_frequency_hz=55)

        self.assertFalse(duplicate["success"])
        self.assertIn("already exists", duplicate["message"])
        self.assertFalse(bad_rating["success"])
        self.assertIn("rated_power_mva must be one of", bad_rating["message"])
        self.assertFalse(bad_group["success"])
        self.assertIn("vector_group must be one of", bad_group["message"])
        self.assertFalse(bad_clock["success"])
        self.assertIn("0 to 11", bad_clock["message"])
        self.assertFalse(bad_frequency["success"])
        self.assertIn("must be 50 or 60", bad_frequency["message"])

    def test_confirmation_prevents_delimiter_name_token_collision(self):
        folder, grid, high_bus, low_bus, app = self.network()
        preview = self.call(
            app,
            transformer_name="A",
            type_name="B WITH C",
        )
        changed_preview = self.call(
            app,
            transformer_name="A WITH B",
            type_name="C",
        )
        self.assertEqual(
            preview["confirmation_required"].split(" plan=")[0],
            changed_preview["confirmation_required"].split(" plan=")[0],
        )
        self.assertNotEqual(
            preview["confirmation_required"],
            changed_preview["confirmation_required"],
        )

        result = self.call(
            app,
            transformer_name="A WITH B",
            type_name="C",
            confirmation=preview["confirmation_required"],
        )
        self.assertFalse(result["success"])
        self.assertIn("confirmation must exactly match", result["message"])
        self.assertEqual(self.transformer_types(folder), [])
        self.assertEqual(grid["ElmTr2"], [])
        self.assertEqual(high_bus["StaCubic"], [])
        self.assertEqual(low_bus["StaCubic"], [])

    def test_confirmation_rejects_active_grid_change(self):
        folder, grid, high_bus, low_bus, app = self.network()
        preview = self.call(app)

        alternate_grid = FakeObject(None, "ElmNet", "Alternate Grid")
        alternate_high = alternate_grid.CreateObject("ElmTerm", "HV Bus")
        alternate_low = alternate_grid.CreateObject("ElmTerm", "LV Bus")
        alternate_high.SetAttribute("uknom", 110.0)
        alternate_low.SetAttribute("uknom", 20.0)
        app.grid = alternate_grid

        result = self.call(app, confirmation=preview["confirmation_required"])

        self.assertFalse(result["success"])
        self.assertIn("confirmation must exactly match", result["message"])
        self.assertEqual(self.transformer_types(folder), [])
        self.assertEqual(grid["ElmTr2"], [])
        self.assertEqual(alternate_grid["ElmTr2"], [])
        self.assertEqual(alternate_high["StaCubic"], [])
        self.assertEqual(alternate_low["StaCubic"], [])

    def test_confirmation_is_bound_to_bus_seed_and_service_state(self):
        folder, grid, high_bus, low_bus, app = self.network()
        alternate_bus = grid.CreateObject("ElmTerm", "Alternate HV Bus")
        alternate_bus.SetAttribute("uknom", 110.0)
        preview = self.call(app)

        changed_requests = (
            {"high_voltage_bus_name": "Alternate HV Bus"},
            {"seed": 43},
            {"out_of_service": True},
            {"transformer_name": "Renamed Transformer"},
        )
        for changes in changed_requests:
            with self.subTest(changes=changes):
                result = self.call(
                    app,
                    confirmation=preview["confirmation_required"],
                    **changes,
                )
                self.assertFalse(result["success"])
                self.assertIn("confirmation must exactly match", result["message"])
                self.assertEqual(self.transformer_types(folder), [])
                self.assertEqual(grid["ElmTr2"], [])
                self.assertEqual(high_bus["StaCubic"], [])
                self.assertEqual(low_bus["StaCubic"], [])


class EvEMTBenchZeroSequenceTest(unittest.TestCase):
    network = EvEMTBenchTransformerTest.network
    call = EvEMTBenchTransformerTest.call
    transformer_types = staticmethod(EvEMTBenchTransformerTest.transformer_types)

    def options(self, **changes):
        result = dict(zero_sequence_model="ynd11_equivalent", r0_r1_ratio=2.15, x0_x1_ratio=0.925)
        result.update(changes)
        return result

    def test_plan_scales_r_and_x_separately_without_changing_positive_samples(self):
        agent = agent_module.DIgSILENTAgent
        for seed in range(20):
            args = ("110/20", 20.0, 60.0, "YNd", 11, "Type", seed)
            baseline = agent._evemtbench_transformer_plan(*args)
            item = agent._evemtbench_transformer_plan(*args, **self.options())
            self.assertEqual(item["powerfactory_attributes"], baseline["powerfactory_attributes"])
            self.assertNotIn("zero_sequence", baseline)
            self.assertEqual(item, agent._evemtbench_transformer_plan(*args, **self.options()))
            attributes = item["powerfactory_attributes"]
            r1 = attributes["pcutr"] / (attributes["strn"] * 1000)
            x1 = ((attributes["uktr"] / 100) ** 2 - r1 ** 2) ** 0.5
            zero = item["zero_sequence"]
            self.assertAlmostEqual(zero["type_attributes"]["r0pu"], 2.15 * r1)
            self.assertAlmostEqual(zero["type_attributes"]["x0pu"], 0.925 * x1)
            self.assertIn("no physical limb/core", zero["limitations"][0])

    def test_preview_and_confirm_verify_type_grounding_and_service_state(self):
        folder, grid, hv, lv, app = self.network()
        preview = self.call(app, **self.options(out_of_service=True))
        self.assertTrue(preview["success"], preview)
        self.assertFalse(preview["applied"])
        self.assertEqual(self.transformer_types(folder), [])
        result = self.call(app, confirmation=preview["confirmation_required"], **self.options(out_of_service=True))
        self.assertTrue(result["success"], result)
        typ = self.transformer_types(folder)[0]
        transformer = grid["ElmTr2"][0]
        self.assertIs(transformer.GetAttribute("typ_id"), typ)
        self.assertEqual(result["retained_element_attributes"]["typ_id"], typ.GetFullName())
        self.assertEqual(transformer.GetAttribute("outserv"), 1)
        for field, value in preview["item"]["zero_sequence"]["element_attributes"].items():
            self.assertEqual(transformer.GetAttribute(field), value)
        for field, value in preview["item"]["zero_sequence"]["derived_type_attributes"].items():
            self.assertAlmostEqual(typ.GetAttribute(field), value)

    def test_default_does_not_assign_zero_sequence_or_grounding(self):
        folder, grid, hv, lv, app = self.network()
        preview = self.call(app)
        result = self.call(app, confirmation=preview["confirmation_required"])
        self.assertTrue(result["success"])
        self.assertNotIn("zero_sequence", result["item"])
        self.assertEqual(self.transformer_types(folder)[0].GetAttribute("x0pu"), 0.03)
        self.assertEqual(grid["ElmTr2"][0].GetAttribute("cgnd_h"), 1)

    def test_unsupported_configurations_and_invalid_ratios_fail_before_connection(self):
        agent = agent_module.DIgSILENTAgent
        base = dict(voltage_class="110/20", rated_power_mva=20.0,
                    nominal_frequency_hz=60.0, vector_group="YNd", clock_number=11,
                    transformer_name="Transformer", type_name="Type",
                    high_voltage_bus_name="HV", low_voltage_bus_name="LV", **self.options())
        changes = [dict(voltage_class="110/11"), dict(rated_power_mva=25),
                   dict(nominal_frequency_hz=50), dict(vector_group="YNyn"),
                   dict(clock_number=5), dict(zero_sequence_model="other"),
                   dict(zero_sequence_model="unchanged")]
        for field, values in (("r0_r1_ratio", (None, True, "2.15", float("nan"), float("inf"), 1.49, 2.81)),
                              ("x0_x1_ratio", (None, True, "0.925", -1, 0.84, 1.01))):
            changes.extend({field: value} for value in values)
        with patch.object(agent, "_get_application") as connect:
            for change in changes:
                with self.subTest(change=change):
                    arguments = dict(base)
                    arguments.update(change)
                    result = agent.create_evemtbench_component("transformer", arguments)
                    self.assertFalse(result["success"], result)
            connect.assert_not_called()

    def test_changed_ratio_model_or_destination_invalidates_confirmation(self):
        folder, grid, hv, lv, app = self.network(with_type_folder=False)
        preview = self.call(app, **self.options())
        for changes in (dict(r0_r1_ratio=2.2), dict(x0_x1_ratio=0.95),
                        dict(zero_sequence_model="unchanged", r0_r1_ratio=None, x0_x1_ratio=None)):
            result = self.call(app, confirmation=preview["confirmation_required"], **self.options(**changes))
            self.assertFalse(result["success"])
            self.assertIn("confirmation must exactly match", result["message"])
        folder.CreateObject("IntPrjfolder", "Transformer Types")
        result = self.call(app, confirmation=preview["confirmation_required"], **self.options())
        self.assertFalse(result["success"])
        self.assertIn("confirmation must exactly match", result["message"])
        self.assertEqual(self.transformer_types(folder), [])
        self.assertEqual(grid["ElmTr2"], [])

    def test_readback_and_grounding_failures_roll_back_type_and_connections(self):
        for rejected in ("r0pu", "x0pu", "cgnd_h"):
            with self.subTest(rejected=rejected):
                folder, grid, hv, lv, app = self.network(with_type_folder=False)
                (grid if rejected == "cgnd_h" else folder).reject_attribute = rejected
                preview = self.call(app, **self.options())
                result = self.call(app, confirmation=preview["confirmation_required"], **self.options())
                self.assertFalse(result["success"], result)
                self.assertTrue(result["rolled_back"], result)
                self.assertEqual(folder["IntPrjfolder"], [])
                self.assertEqual(grid["ElmTr2"], [])
                self.assertEqual(hv["StaCubic"], [])
                self.assertEqual(lv["StaCubic"], [])

    def test_partial_element_rollback_preserves_its_type(self):
        folder, grid, hv, lv, app = self.network()
        grid.reject_attribute = "cgnd_h"
        preview = self.call(app, **self.options())
        create = FakeObject.CreateObject
        def cannot_delete(parent, class_name, name):
            obj = create(parent, class_name, name)
            if class_name == "ElmTr2":
                obj.delete_fails = True
            return obj
        with patch.object(FakeObject, "CreateObject", cannot_delete):
            result = self.call(app, confirmation=preview["confirmation_required"], **self.options())
        self.assertFalse(result["success"])
        self.assertFalse(result["rolled_back"])
        self.assertTrue(result["type_created"])
        self.assertIn("remaining_transformer", result)
        self.assertEqual(len(self.transformer_types(folder)), 1)

    def test_listing_advertises_optional_inputs_and_partial_mapping(self):
        listing = agent_module.DIgSILENTAgent.list_evemtbench_components("transformer")
        self.assertEqual(listing["creation_parameters"]["zero_sequence_model"]["default"], "unchanged")
        self.assertTrue(listing["creation_parameters"]["r0_r1_ratio"]["nullable"])
        self.assertIn("partial_table_10_mapping", listing)
        self.assertEqual(listing["unmapped_source_tables"], [10, 12])

    def test_derived_zero_sequence_verification_failure_cleans_new_folder(self):
        folder, grid, hv, lv, app = self.network(with_type_folder=False)
        preview = self.call(app, **self.options())
        original = FakeObject.GetAttribute
        def bad_derived(obj, key):
            if obj.class_name == "TypTr2" and key == "uk0tr":
                return 999.0
            return original(obj, key)
        with patch.object(FakeObject, "GetAttribute", bad_derived):
            result = self.call(app, confirmation=preview["confirmation_required"], **self.options())
        self.assertFalse(result["success"])
        self.assertTrue(result["rolled_back"])
        self.assertEqual(folder["IntPrjfolder"], [])
        self.assertEqual(grid["ElmTr2"], [])

    def test_database_failure_remains_a_structured_error(self):
        folder, grid, hv, lv, app = self.network()
        with patch.object(agent_module.DIgSILENTAgent, "_load_evemtbench_database",
                          side_effect=RuntimeError("database unavailable")):
            result = self.call(app, **self.options())
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "database unavailable")
        self.assertEqual(self.transformer_types(folder), [])


if __name__ == "__main__":
    unittest.main()
