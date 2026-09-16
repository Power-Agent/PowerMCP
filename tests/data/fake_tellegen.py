"""A stand-in for the compiled `tellegen` CLI, speaking its JSON protocol.

The PowerMCP tellegen server runs a `.py` binary through the current
interpreter, so this file exercises every subprocess path in CI without a Rust
toolchain. It records what it received so tests can assert on the hand-off:
`FAKE_TELLEGEN_RECORD` names a file that gets the argv and stdin of each call.
`FAKE_TELLEGEN_SLEEP` makes the process block that many seconds (cancellation
tests) and `FAKE_TELLEGEN_ROWS` sizes the arrays of a solve response.
"""
import json
import os
import signal
import sys
import time


def _record(argv, stdin_text):
    path = os.environ.get("FAKE_TELLEGEN_RECORD")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"argv": argv, "stdin": stdin_text}) + "\n")


def _sleep():
    seconds = float(os.environ.get("FAKE_TELLEGEN_SLEEP", "0") or 0)
    if seconds <= 0:
        return

    def cancelled(*_):
        print("tellegen: cancelled; saved the completed trials", file=sys.stderr)
        sys.exit(1)

    signal.signal(signal.SIGTERM, cancelled)
    signal.signal(signal.SIGINT, cancelled)
    time.sleep(seconds)


def _module(stdin_text):
    module = json.loads(stdin_text)
    if module.get("schema") != "pio-ir" or module.get("version") != 2:
        print("tellegen: electrical inputs require PowerIO IR generation 2", file=sys.stderr)
        sys.exit(1)
    return module


def _solution(module):
    # The real CLI returns a powerio.DcOpfSolution module. The stand-in keeps
    # the network value, which PowerIO still deserializes, and marks itself as
    # the producer so a test can tell the round trip happened.
    module = dict(module)
    module["producer"] = {"name": "fake-tellegen", "version": "0.0.0"}
    return module


def main(argv):
    arg = argv[1] if len(argv) > 1 else ""
    stdin_text = "" if arg in ("capabilities", "contract", "-h", "--help") else sys.stdin.read()
    _record(argv[1:], stdin_text)
    if arg == "capabilities":
        print(json.dumps([{"formulation": "dcopf", "available": True}, {"formulation": "acopf", "available": False}]))
        return 0
    if arg == "contract":
        print(json.dumps({"contract": "tellegen.cli/1", "tellegen_version": "0.3.0-fake", "powerio_version": "0.11.2", "schemas": {}}))
        return 0
    if arg == "boom":
        print("tellegen: boom", file=sys.stderr)
        return 1
    _sleep()
    if arg == "solve-module":
        # Tellegen accepts a network or a DC OPF instance and returns a solution module.
        print(json.dumps(_solution(_module(stdin_text))))
        return 0
    if arg == "plan":
        request = json.loads(stdin_text)
        module = request["module"]
        if module.get("schema") != "pio-ir":
            print("tellegen: unreadable planning request", file=sys.stderr)
            return 1
        print(json.dumps({"plan": {"spec": request["spec"], "trials": [{"objective": 1.0}]}, "solution_module": _solution(module)}))
        return 0
    if arg == "study":
        command, path = argv[2], argv[3]
        if command == "create":
            request = json.loads(stdin_text)
            bundle = {"document": {"id": request.get("id", "s"), "revision": 1, "active_goal": "g",
                                   "goals": {"g": {"request": request.get("request", ""), "anchor_state": "base"}},
                                   "states": {"base": {}}, "experiments": {}},
                      "artifacts": {}, "input_has_ir": request.get("input", "").startswith("{")}
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(bundle, handle)
            print(json.dumps({"id": bundle["document"]["id"], "revision": 1, "active_goal": ["g", bundle["document"]["goals"]["g"]]}))
            return 0
        with open(path, encoding="utf-8") as handle:
            bundle = json.load(handle)
        if command == "inspect":
            print(json.dumps({"id": bundle["document"]["id"], "revision": bundle["document"]["revision"]}))
            return 0
        if command == "export":
            print(json.dumps(bundle))
            return 0
        if command == "run":
            request = json.loads(stdin_text)
            if request["operation"].get("kind") == "apply":
                with open(path + ".applied", "w", encoding="utf-8") as marker:
                    marker.write("applied")
            if "--progress" in argv:
                # A progress event names itself; the trial log line beside it is
                # ordinary stderr text and must not be read as one.
                print(json.dumps({"trial": 1, "objective": 1.0}), file=sys.stderr)
                print(json.dumps({"event": "study_checkpoint", "index": 1}), file=sys.stderr)
            bundle["document"]["revision"] += 1
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(bundle, handle)
            print(json.dumps({"summary": {"id": bundle["document"]["id"], "revision": bundle["document"]["revision"]},
                              "experiment": "e1"}))
            return 0
        print("tellegen: unknown Study command", file=sys.stderr)
        return 1
    # A solve request: the module on stdin, the request in argv.
    request = json.loads(arg or "{}")
    module = _module(stdin_text)
    buses = module["value"]["data"].get("buses") or []
    rows = int(os.environ.get("FAKE_TELLEGEN_ROWS", str(len(buses)) if buses else "3"))
    print(json.dumps({"formulation": request.get("formulation", "dcopf"), "status": "optimal", "objective": 1.0,
                      "request": request, "lmp": [{"id": i + 1, "value": 1.0} for i in range(rows)]}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
