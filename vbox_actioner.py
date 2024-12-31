import ast
import sys
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
from time import sleep

import yaml

def syntax_check(script_fn):
    try:
        with open(script_fn, "r", encoding="utf-8") as f:
            script_content = f.read()
        ast.parse(script_content, filename=str(script_fn))
        print(f"Syntax check passed: {script_fn}")
        return True
    except SyntaxError as e:
        print(f"Syntax error in {script_fn}: {e}")
        return False

def execute_script(script_fn):
    script_dn = str(script_fn.parent)

    added = script_dn not in sys.path
    if added:
        sys.path.insert(0, script_dn)

    try:
        spec = spec_from_file_location('plugin_script', script_fn)
        plugin_module = module_from_spec(spec)
        spec.loader.exec_module(plugin_module)
    finally:
        if added:
            sys.path.remove(script_dn)

def _main():
    if len(sys.argv) > 2:
        print("Too many arguments.", file=sys.stderr)
        sys.exit(1)

    arg = sys.argv[1] if len(sys.argv) == 2 else 'config.yaml'
    config_fn = Path(arg).absolute()
    if not config_fn.is_file():
        print("Config file is not found: {setup_fn}")
        sys.exit(1)

    print(f"Load config file: {config_fn}")
    with open(config_fn, 'r', encoding='utf-8') as fin:
        config = yaml.safe_load(fin)

    if 'lib_dn' in config:
        lib_dn = Path(config['lib_dn']).absolute()
        if not lib_dn.is_dir():
            print(f"Library directory is not found: {lib_dn}")
            sys.exit(1)
        sys.path.insert(0, str(lib_dn))
    else:
        lib_dn = None

    script_fn = Path(config['script_fn']).absolute()
    if not script_fn.is_file():
        print(f"Script file is not found: {script_fn}")
        sys.exit(1)

    machine_name = config.get('machine_name')
    if not machine_name:
        print("No machine_name in config")
        sys.exit(1)

    snapshot_name = config.get('snapshot_name')
    if not snapshot_name:
        print("No snapshot_name in config")
        sys.exit(1)

    if not syntax_check(script_fn):
        sys.exit(1)

    print(f"  Script file: {script_fn}")
    print(f"  Library directory: {lib_dn}")
    print(f"  Machine name: {machine_name}")
    print(f"  Snapshot name: {snapshot_name}")

    environment = __import__('environment').environment

    def get(name, cast):
        return cast(config.get(name, environment.get(name)))

    environment.script_fn = script_fn
    environment.machine_name = machine_name
    environment.snapshot_name = snapshot_name
    environment.start_pause = get('start_pause', int)
    environment.time_scale = get('time_scale', float)

    providers = ('logger', 'video', 'effector', 'ocr')
    for provider in providers:
        __import__(f'providers.{provider}')

    log = __import__('log')
    vbox_vm = __import__('vbox_vm')
    __import__('detectors')
    with vbox_vm.create() as vm:
        try:
            environment.vm = vm
            vm.go()

            log.notice("Pause before script execution")
            sleep(0.9 * environment.start_pause)
            environment.ready = True
            sleep(0.1 * environment.start_pause)

            log.notice(f"Start executing: {script_fn}")
            execute_script(script_fn)
        except Exception as e: #pylint: disable=broad-exception-caught
            stype = e.__class__.__name__
            log.error(f"Exception {stype} in script {script_fn}: {e}")
        environment.basta = True

        for component in environment.components.values():
            if hasattr(component, 'deinit'):
                component.deinit()

if __name__ == '__main__':
    _main()
