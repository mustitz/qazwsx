import os
import subprocess

from argparse import ArgumentParser
from queue import Queue, Empty as QueueIsEmpty
from subprocess import Popen, PIPE
from threading import Thread
from time import time, sleep

import yaml

import setup

settings = {
    'last_num': 0,
    'log_file': None,
    'print': True,
}

Popen = subprocess.Popen
PIPE = subprocess.PIPE

if os.name == 'nt':
    CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW

    try:
        import console_ctrl
        send_ctrl_c = console_ctrl.send_ctrl_c
    except ModuleNotFoundError:
        def send_ctrl_c(_):
            if not settings.get('warn-missed-ctrl-c', False):
                settings['warn-missed-ctrl-c'] = True
                echo("Warn: Import console_ctrl not found, miss sending Ctrl+C")

    def kill(pid):
        kill_cmd = f"taskkill /F /PID {pid}"
        os.system(kill_cmd)


else:
    def send_ctrl_c(pid):
        kill_cmd = f"kill {pid}"
        os.system(kill_cmd)

    def kill(pid):
        kill_cmd = f"kill -9 {pid}"
        os.system(kill_cmd)

    CREATE_NO_WINDOW = 0



def now():
    return time()

def wait(delay):
    if delay > 0.0:
        sleep(delay)

def echo(msg):
    if settings.get('print', False):
        print(msg)

    fn = settings.get('log_file', None)
    if fn is not None:
        with open(fn, 'a', encoding='utf-8') as outf:
            print(msg, file=outf)

def get_script_log_dn():
    last_num = settings.get('last_num', 0) + 1
    while True:
        log_dn = setup.SCRIPT_LOG_DN / f'{last_num:05d}'
        if not log_dn.is_dir():
            break

        last_num += 1

    settings['last_num'] = last_num

    log_dn = log_dn.absolute()
    log_dn.mkdir(parents=True)
    return log_dn

def reader_thread_func(marker, pipe, queue):
    while True:
        line = pipe.readline()
        if not line:
            break

        queue.put(marker + line.rstrip())

def start_reader_thread(marker, pipe, q):
    thread = Thread(target=reader_thread_func, args=(marker, pipe, q))
    thread.start()
    return thread

def flush_queue(queue):
    while True:
        try:
            line = queue.get_nowait()
        except QueueIsEmpty:
            break

        echo(line)

def do_script(**kwargs):
    script_fn_arg = kwargs.pop('script_fn', None)
    if script_fn_arg is None:
        echo("Script file is not set")
        return

    script_fn = None
    for prefix in setup.SCRIPT_PREFIXES:
        fn = prefix / script_fn_arg
        if fn.is_file():
            script_fn = fn.absolute()
            break

    if script_fn is None:
        echo(f"Script file is not found: {script_fn}")
        return
    kwargs['script_fn'] = str(script_fn)

    timeout = kwargs.pop('timeout', None)
    if (timeout is None) or (timeout <= 0):
        timeout = 10 * 365 * 24 * 3600 # 10 years

    log_dn = kwargs.pop('log_dn', None)
    if log_dn is None:
        log_dn = get_script_log_dn()
    kwargs['log_dn'] = str(log_dn)

    lib_dn = kwargs.pop('lib_dn', None)
    if lib_dn is None:
        lib_dn = setup.PROJECT_DN / 'lib'
    kwargs['lib_dn']  = str(lib_dn)

    settings['log_file'] = log_dn / 'run.log'
    echo(f"Started test in {log_dn}")

    config_fn = log_dn / 'config.yaml'
    with open(config_fn, 'w', encoding='utf-8') as outf:
        yaml.dump(kwargs, outf,
            default_flow_style=False,
            sort_keys=False
            )
    echo(f"Written config in {config_fn}")

    if os.name == 'nt':
        python_fn = setup.VENV_DN / 'Scripts' / 'python.exe'
    else:
        python_fn = setup.VENV_DN / 'bin' / 'python'
    echo(f"Use python: {python_fn}")

    runner_fn = setup.PROJECT_DN / 'vbox_actioner.py'
    echo(f"Runner: {runner_fn}")

    cmd = [ python_fn, runner_fn ]
    echo("Starting...")

    terminated, killed = False, False
    queue = Queue()
    with Popen(cmd,
            stdout=PIPE, stderr=PIPE,
            cwd=log_dn,
            creationflags=CREATE_NO_WINDOW,
            encoding='utf-8',
            ) as process:
        echo(f"vbox_actioner PID: {process.pid}")
        stdout_reader = start_reader_thread('1> ', process.stdout, queue)
        stderr_reader = start_reader_thread('2> ', process.stderr, queue)

        starting_at = now()
        while True:
            wait(1)

            exit_code = process.poll()
            if exit_code is not None:
                break

            flush_queue(queue)

            duration = now() - starting_at

            if duration > timeout + 5:
                if not killed:
                    echo(f"Warn: Kill vbox_actioner with PID {process.pid}")
                    kill(process.pid)
                    killed = True

            if duration > timeout:
                if not terminated:
                    echo(f"Terminate vbox_actioner with PID {process.pid}")
                    send_ctrl_c(process.pid)
                    terminated = True

        stdout_reader.join()
        stderr_reader.join()
        flush_queue(queue)

    if exit_code >= 0x80000000:
        exit_code = hex(exit_code)
    echo(f"Finished with code {exit_code}")



def _main():
    parser = ArgumentParser(description='Run script cli')

    parser.add_argument('script_fn', type=str,
        help='Script to execute')

    parser.add_argument('machine_name', type=str,
        help='Name of the virtual machine')

    parser.add_argument('snapshot_name', type=str, nargs='?', default=None,
        help='Name of the snapshot (optional)')

    parser.add_argument('-t', '--timeout', type=int, default=60,
        help='Timeout value in seconds (default: 60)')

    parser.add_argument('-p', '--start-pause', type=int, default=10,
        help='Pause after turn on (default: 10)')

    args = parser.parse_args()
    do_script(**{
        'script_fn': args.script_fn,
        'machine_name': args.machine_name,
        'snapshot_name' : args.snapshot_name,
        'timeout': args.timeout,
        'start_pause': args.start_pause,
        })

if __name__ == '__main__':
    _main()
