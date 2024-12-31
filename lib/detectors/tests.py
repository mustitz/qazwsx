import log
from testing import run_bundle, isok, failed, passed
from imgrect import ImgRect

def cross_detector_test(test_config): #pylint: disable=too-many-return-statements
    log.info("Test params:")
    for k, v in test_config.items():
        log.info(f"  {k}={v}")

    img_fn = test_config['test_dn'] / test_config.img
    log.info(f"  image file: {img_fn}")
    img = ImgRect.load(img_fn)

    expected_ok = isok(test_config['result'])
    detection = img.detect('cross')
    if detection is None:
        if expected_ok:
            return failed("detection failure, cross has not been found!")
        return passed("no cross as expected")

    if not expected_ok:
        return failed("found something but not expected")

    x, y = test_config['center']
    w, h = test_config['sides']
    minprob = test_config['minprob']

    x1, y1, x2, y2 = detection.rect
    goodx = x1 <= x <= x2
    goody = y1 <= y <= y2
    if not goodx or not goody:
        return failed(f"center {(x, y)} is not in detection rect {detection.rect}")

    rw, rh = detection.rect.width, detection.rect.height
    if abs(w - rw) > 2 or abs(h - rh) > 2:
        return failed(f"very big shape difference: {w}x{h} abd {rw}x{rh}")

    p = detection.probability
    if p < minprob:
        return failed(f"low probability {p:.03f}, at least {minprob:.03f} is needed.")

    return passed(f"{detection}")

def panel_detector_test(test_config): #pylint: disable=too-many-return-statements
    log.info("Test params:")
    log.shift(+1)
    try:
        for k, v in test_config.items():
            log.info(f"{k}={v}")
    finally:
        log.shift(-1)

    img_fn = test_config['test_dn'] / test_config.img
    log.info(f"Image file: {img_fn}")
    img = ImgRect.load(img_fn)

    expected_ok = isok(test_config['result'])
    x, y = test_config['point']
    detection = img.detect('panels')
    log.notice(f"Detected: {detection}")
    log.warn("Not implemented: check detection")

def run():
    #run_bundle('cross_detector', cross_detector_test)
    run_bundle('panel_detector', panel_detector_test)
