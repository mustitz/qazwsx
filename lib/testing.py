import os
from pathlib import Path

import cv2
import yaml
import numpy as np
from easydict import EasyDict

import log
from environment import environment
from imgrect import ImgRect

def imdebug(name, img, *args):
    if environment.test is None:
        return
    num = environment.test.qimages
    environment.test.qimages += 1

    if isinstance(img, ImgRect):
        img = img.buf

    if args:
        img = np.copy(img)
        for art_func in args:
            art_func(img=img)
    cv2.imwrite(f'{num:04d}-{name}.png', img)

def isok(s):
    return s.lower() == 'ok'

def failed(msg):
    log.error(f"    FAIL - {msg}")
    return False

def passed(msg):
    log.notice(f"    PASS - {msg}")
    return True

def istest():
    return environment.test is not None


def run_test(func, test_fn, test_dn):
    with open(test_fn, 'r', encoding='utf-8') as fin:
        test_config = EasyDict(yaml.safe_load(fin))

    test_config['test_dn'] = test_dn

    name = test_config['name']

    num = environment.test.get('num', 1)
    environment.test.num += 1

    current_dn = Path('.').absolute()
    work_dn = Path(f'{num:04d}-{name}').absolute()
    work_dn.mkdir(parents=True, exist_ok=True)

    log.notice(f"Run test {name} in {work_dn}:")
    log.shift(+1)
    os.chdir(work_dn)
    try:
        environment.test.qimages = 1
        func(test_config)
    finally:
        os.chdir(current_dn)
        log.shift(-1)

def run_bundle(bundle_name, func):
    data_dn = environment.user_data['data_dn']
    test_dn = data_dn / bundle_name
    log.notice(f"Run test bundle: {bundle_name} from {test_dn}")

    log.shift(+1)
    try:
        for test_fn in sorted(test_dn.glob('*.yaml')):
            run_test(func, test_fn, test_dn)
    finally:
        log.shift(-1)

def _init():
    environment.test = EasyDict()
    environment.test.num = 1
    environment.test.qimages = 1

_init()
