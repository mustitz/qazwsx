import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import cv2
import easyocr
import numpy as np

PORT = 1914
BASE_DN = Path.home() / 'data' / 'qazwsx'
FONT = cv2.FONT_HERSHEY_SIMPLEX

readers = {}

class BadParams(Exception):
    pass

def get_reader(langs):
    key = ':'.join(langs)
    result = readers.get(key)
    if result:
        return result

    result = easyocr.Reader(langs,
        model_storage_directory=BASE_DN / 'easyocr',
        gpu=True, verbose=True,
    )

    print('Created reader', key)
    readers[key] = result
    return result

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self): #pylint: disable=invalid-name
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)

        try:
            lang = query_params.get('lang')
            if lang:
                lang = lang[0]

            if lang == 'en':
                lang = None

            langs = ['en']
            if lang:
                langs.append(lang)

            fn_param = query_params.get('fn')
            if not fn_param:
                raise BadParams("No fn in query_params")

            fn = Path(fn_param[0])
            if not fn.is_file():
                raise BadParams(f"File not found: {fn}, {fn_param}")

            fn = str(fn.absolute())
            if fn[-4:] == '.png':
                img = cv2.imread(fn)
            elif fn[-4:] == '.npy':
                img = np.load(fn)
            else:
                raise BadParams("Unsupported file format")

            reader = get_reader(langs)
            ocrs = list(reader.readtext(img))

            response = {
                'status': 'OK',
                'texts': [str(item) for item in ocrs],
            }

            self.send_response(200)
        except Exception as e:
            response = {
                'status': 'FAIL',
                'message': str(e)
            }

            self.send_response(400)
            raise

        self.send_header("Content-Type", "application/json")
        self.end_headers()

        self.wfile.write(json.dumps(response).encode("utf-8"))
        self.wfile.write(b'\n')
        self.wfile.flush()
        self.connection.close()

        if img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        for i, (bbox, _, prob) in enumerate(ocrs):
            tl, tr, br, bl = bbox
            tl = (int(tl[0]), int(tl[1]))
            tr = (int(tr[0]), int(tr[1]))
            br = (int(br[0]), int(br[1]))
            bl = (int(bl[0]), int(bl[1]))

            p, q = prob ** 2, 1.0 - prob ** 2
            color = (0, 128 + int(p * 127), 128 + int(q * 127))
            cv2.rectangle(img, tl, br, color=color, thickness=2)

            x, y = tl[0], tl[1] - 10
            if y < 50:
                y = bl[1] + 13

            cv2.putText(img, str(i), (x, y), FONT, 0.5, color, 1)

        png_fn = fn[:-4] + '.ocr.png'
        cv2.imwrite(png_fn, img)

        log_fn = fn[:-4] + '.log'
        with open(log_fn, 'w', encoding='utf-8') as f:
            for i, t in enumerate(ocrs):
                line = ' '.join(str(v) for v in t)
                f.write(f"{i:02d}: {line}\n")


def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler, port=None):
    port = port or PORT
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting http server on port {port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
