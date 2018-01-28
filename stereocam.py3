#!/usr/bin/python3

import select
import v4l2capture
from PIL import Image
from io import BytesIO
from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import os

def mergeImages(file1, file2):
    """Merge two images into one, displayed side by side
    :param file1: path to first image file
    :param file2: path to second image file
    :return: the merged Image object
    """
    image1 = Image.open(file1)
    image2 = Image.open(file2)

    image1 = image1.rotate(180)
    image2 = image2.rotate(180)

    (width1, height1) = image1.size
    (width2, height2) = image2.size

    result_width = width1 + width2
    result_height = max(height1, height2)

    result = Image.new('RGB', (result_width, result_height))
    result.paste(im=image1, box=(0, 0))
    result.paste(im=image2, box=(width1, 0))
    return result


class mjpg_RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if (self.path == '/stereo.mjpg'):

            video1 = v4l2capture.Video_device("/dev/video1")
            video2 = v4l2capture.Video_device("/dev/video0")

            size_x1, size_y1 = video1.set_format(640, 480, fourcc='MJPG')
            size_x2, size_y2 = video2.set_format(640, 480, fourcc='MJPG')

            video1.create_buffers(1)
            video2.create_buffers(1)

            video1.queue_all_buffers()
            video2.queue_all_buffers()

            video1.start()
            video2.start()

            self.send_response(200)
            self.send_header('Content-type','multipart/x-mixed-replace; boundary=--jpgboundary')
            self.end_headers()

            print(self.path)

            while True:
                try:
                    select.select((video1,), (), ())
                    select.select((video2,), (), ())

                    imageIo = BytesIO()

                    img1 = video1.read_and_queue()
                    img2 = video2.read_and_queue()

                    imgMerge = mergeImages(BytesIO(img1), BytesIO(img2))
                    imgMerge.save(imageIo, format="JPEG")

                    self.wfile.write(b"--jpgboundary\n")
                    self.send_header('Content-type', 'image/jpeg')
                    self.send_header('Content-length', len(imageIo.getvalue()))
                    self.end_headers()
                    self.wfile.write(imageIo.getvalue())

                    time.sleep(0.07)

                except BrokenPipeError:
                    video1.close()
                    video2.close()
                    print("Closed Cameras\n")
                    return

        elif os.path.isfile('.' + self.path):
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.send_header('Content-length', os.stat('.' + self.path).st_size)
            self.end_headers()
            self.wfile.write(open(('.' + self.path), "rb").read())


print("Starting HTTP server")
serverAddress = ('0.0.0.0', 9998)
httpd = HTTPServer(serverAddress, mjpg_RequestHandler)
print('running server...')
httpd.serve_forever()

