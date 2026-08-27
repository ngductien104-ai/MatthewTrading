"""The bash tool must hand agents the interpreter the swarm itself runs on.

Running a virtualenv's python does not put its Scripts/bin on PATH, so before
this was pinned a bare ``python`` in an agent's shell resolved to an unrelated
runtime with none of the data packages. In a live FPT run on 2026-08-27 the
quality analyst concluded vnstock_data "is not available in the runtime" and
sourced a buy-side report from Wikipedia instead. A silent downgrade to a worse
source is the worst failure this repo has, so it gets a test.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from src.tools.bash_tool import BashTool, _child_env


class TestChildEnv:
    def test_the_running_interpreters_directory_comes_first_on_path(self):
        env = _child_env()
        first = env["PATH"].split(os.pathsep)[0]
        assert Path(first) == Path(sys.executable).resolve().parent

    def test_the_rest_of_the_environment_is_preserved(self):
        env = _child_env()
        assert env.get("PATH") != os.environ.get("PATH")
        for key in os.environ:
            if key != "PATH":
                assert env[key] == os.environ[key]


class TestResolvedInterpreter:
    def test_a_bare_python_resolves_to_the_swarm_interpreter(self):
        out = json.loads(BashTool().execute(
            command='python -c "import sys; print(sys.executable)"'
        ))
        assert out["exit_code"] == 0, out
        assert Path(out["stdout"].strip()) == Path(sys.executable)

    def test_the_data_layer_imports_in_that_interpreter(self):
        """The exact check the FPT quality analyst got wrong."""
        out = json.loads(BashTool().execute(
            command='python -c "import vnstock_data; print(vnstock_data.__name__)"'
        ))
        assert out["exit_code"] == 0, out
        assert "vnstock_data" in out["stdout"]
