from PyQt5 import QtCore, QtWidgets
from threading import Thread
from collections import deque
import sys
import cv2
import numpy
import time
import base64
import sys
import socket
from datetime import datetime
from docopt import docopt

help = """Server (Cameras video stream catcher).

Usage:
  multi_cameras.py [--host=<hs>] [--port=<ps>]
  multi_cameras.py (-h | --help)
  multi_cameras.py --version

Options:
  -h --help             Show this screen.
  --version             Show version.
  --host=<hs>           Host for server reciever                           [default: 92.53.105.143].
  --port=<ps>           Port for server reciever                           [default: 9000]. 
"""

class CameraWidget(QtWidgets.QWidget):
    def __init__(self, stream_link=0, parent=None, deque_size=1, arguments={}):
        super(CameraWidget, self).__init__(parent)
        
        # Очередь для кадров
        self.deque = deque(maxlen=deque_size)

        self.camera_stream_link = stream_link

        self.online = False
        self.capture = None
        self.video_frame = QtWidgets.QLabel()

        self.TCP_SERVER_IP = arguments['--host']
        self.TCP_SERVER_PORT = int(arguments['--port'])
        self.connectCount = 0
        self.connectServer()

        self.load_network_stream()
        
        # Процесс по захвату кадров
        self.get_frame_thread = Thread(target=self.get_frame, args=())
        self.get_frame_thread.daemon = True
        self.get_frame_thread.start()

        # Отправка кадров через интервал
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.set_frame)
        self.timer.start(.9)

        print('Started camera: {}'.format(self.camera_stream_link))

    def load_network_stream(self):
        def load_network_stream_thread():
            if self.verify_network_stream(self.camera_stream_link):
                self.capture = cv2.VideoCapture(self.camera_stream_link)
                self.online = True
        self.load_stream_thread = Thread(target=load_network_stream_thread, args=())
        self.load_stream_thread.daemon = True
        self.load_stream_thread.start()

    def verify_network_stream(self, link):
        cap = cv2.VideoCapture(link)
        if not cap.isOpened():
            return False
        cap.release()
        return True

    def get_frame(self):
        while True:
            try:
                if self.capture.isOpened() and self.online:
                    # Считывание кадра
                    status, frame = self.capture.read()
                    if status:
                        self.deque.append(frame)
                    else:
                        self.capture.release()
                        self.online = False
                else:
                    # Попытка переподключения
                    print('attempting to reconnect', self.camera_stream_link)
                    self.load_network_stream()
                    self.spin(2)
                self.spin(.001)
            except AttributeError:
                pass
    
    def connectServer(self):
        try:
            self.sock = socket.socket()
            self.sock.connect((self.TCP_SERVER_IP, self.TCP_SERVER_PORT))
            print(u'Client socket is connected with Server socket [ TCP_SERVER_IP: ' + self.TCP_SERVER_IP + ', TCP_SERVER_PORT: ' + str(self.TCP_SERVER_PORT) + ' ]')
            self.connectCount = 0
        except Exception as e:
            print(e)
            self.connectCount += 1
            if self.connectCount == 10:
                print(u'Connect fail %d times. exit program'%(self.connectCount))
                sys.exit()
            print(u'%d times try to connect with server'%(self.connectCount))
            self.connectServer()

    def spin(self, seconds):
        time_end = time.time() + seconds
        while time.time() < time_end:
            QtWidgets.QApplication.processEvents()

    def set_frame(self):

        if not self.online:
            self.spin(1)
            return

        if self.deque and self.online:
            # Получение кадра из очереди
            frame = self.deque[-1]
            resize_frame = cv2.resize(frame, dsize=(480, 315), interpolation=cv2.INTER_AREA)

            now = time.localtime()
            stime = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
                    
            encode_param=[int(cv2.IMWRITE_JPEG_QUALITY),90]
            result, imgencode = cv2.imencode('.jpg', resize_frame, encode_param)
            data = numpy.array(imgencode)
            stringData = base64.b64encode(data)
            length = str(len(stringData))
            self.sock.sendall(length.encode('utf-8').ljust(64))
            self.sock.send(stringData)
            self.sock.send(stime.encode('utf-8').ljust(64))

    def get_video_frame(self):
        return self.video_frame
    
def exit_application():
    """Exit program event handler"""
    sys.exit(1)

if __name__ == '__main__':
    arguments = docopt(help, version='Server (Cameras catcher)')
    print(arguments)
    # Create main application window
    app = QtWidgets.QApplication([])
    app.setStyle(QtWidgets.QStyleFactory.create("Cleanlooks"))
    '''mw = QtWidgets.QMainWindow()
    mw.setWindowTitle('Camera GUI')
    mw.setWindowFlags(QtCore.Qt.FramelessWindowHint)

    cw = QtWidgets.QWidget()
    ml = QtWidgets.QGridLayout()
    cw.setLayout(ml)
    mw.setCentralWidget(cw)
    mw.showMaximized()'''
    
    # Stream links
    camera0 = 'http://192.168.0.97:4747/video'
    camera1 = 'http://172.20.10.13:4747/video'
    '''camera2 = 'http://192.168.0.98:4747/video'
    camera3 = 'http://192.168.0.97:4747/video'
    camera4 = 'http://192.168.0.97:4747/video'
    camera5 = 'http://192.168.0.97:4747/video'
    camera6 = 'http://192.168.0.97:4747/video'
    camera7 = 'http://192.168.0.97:4747/video' '''
    
    # Create camera widgets
    print('Creating Camera Widgets...')
    zero = CameraWidget(0,arguments=arguments)
    one = CameraWidget(camera1,arguments=arguments)

    zero.get_video_frame()
    one.get_video_frame()
    '''two = CameraWidget(screen_width//3, screen_height//3, camera2)
    three = CameraWidget(screen_width//3, screen_height//3, camera3)
    four = CameraWidget(screen_width//3, screen_height//3, camera4)
    five = CameraWidget(screen_width//3, screen_height//3, camera5)
    six = CameraWidget(screen_width//3, screen_height//3, camera6)
    seven = CameraWidget(screen_width//3, screen_height//3, camera7)'''

    #mw.show()

    #QtWidgets.QShortcut(QtWidgets.QKeySequence('Ctrl+Q'), mw, exit_application)

    if(sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtWidgets.QApplication.instance().exec_()