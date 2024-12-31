import os
import sys
from collections import namedtuple
from pathlib import Path

import setup

MY_FN = Path(__file__).absolute()
MY_DN = MY_FN.parent

DebugEnv = namedtuple('DebugEnv', ['work_dn', 'lib_dn'])

def init_debug_environmet():
    lib_dn = str(MY_DN / 'lib')

    missed = lib_dn not in sys.path
    if missed:
        sys.path.insert(0, lib_dn)
    else:
        lib_dn = None

    log_dn = (setup.SCRIPT_LOG_DN.parent / 'tests').absolute()
    log_dn.mkdir(parents=True, exist_ok=True)

    num = 0
    while True:
        num += 1
        work_dn = log_dn / f'{num:05d}'
        if not work_dn.is_dir():
            break

    work_dn = work_dn.absolute()
    work_dn.mkdir(parents=True)
    os.chdir(work_dn)

    return DebugEnv(work_dn, lib_dn)

def deinit_debug_environment(debug_env):
    lib_dn = debug_env.lib_dn
    if lib_dn:
        sys.path.remove(lib_dn)

def _main():
    debug_env = init_debug_environmet()
    try:
        environment = __import__('environment').environment
        environment.test_num = 1
        environment.script_fn = MY_FN

        _, *data_dirs = sys.argv
        if len(data_dirs) == 0:
            data_dirs = [ MY_DN / 'data' ]

        providers = ('logger', )
        for provider in providers:
            __import__(f'providers.{provider}')

        log = __import__('log')
        detectors = __import__('detectors')
        tests = detectors.tests

        log.notice(f"Run tests in {debug_env.work_dn}")
        for dn in data_dirs:
            dn = Path(dn).absolute()
            environment.user_data.data_dn = dn

            log.shift(+1)
            try:
                log.notice(f"Use test data: {dn}")
                log.shift(+1)
                try:
                    tests.run()
                finally:
                    log.shift(-1)
            finally:
                log.shift(-1)

    finally:
        deinit_debug_environment(debug_env)

if __name__ == '__main__':
    _main()
