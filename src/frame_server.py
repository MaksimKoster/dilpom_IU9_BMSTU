import multiprocessing
import socket
import os
import cv2
import numpy
import base64
import time
from datetime import datetime
import os
import pickle
from PIL import Image, ImageDraw
import face_recognition
import numpy as np
import paho.mqtt.publish as publish
from docopt import docopt
import clickhouse_connect

help = """Server (Cameras reciever).

Usage:
  frame_server.py [--host=<hs>] [--port=<ps>] [--remote_host=<rh>] [--remote_port_web=<wb>]
  frame_server.py (-h | --help)
  frame_server.py --version

Options:
  -h --help             Show this screen.
  --version             Show version.
  --host=<hs>           Host for server                            [default: 127.0.0.1].
  --port=<ps>           Port for server                            [default: 9000]. 
  --remote_host=<rh>    MQTT broker host                           [default: 92.53.105.143].
  --remote_port_web=<wb> Web server port on this server    [default: 11000].
"""


def predict(X_frame, knn_clf=None, model_path=None, distance_threshold=0.5):
    if knn_clf is None and model_path is None:
        raise Exception("Must supply knn classifier either thourgh knn_clf or model_path")

    if knn_clf is None:
        with open(model_path, 'rb') as f:
            knn_clf = pickle.load(f)

    X_face_locations = face_recognition.face_locations(X_frame)

    # Нет лиц
    if len(X_face_locations) == 0:
        return []

    faces_encodings = face_recognition.face_encodings(X_frame, known_face_locations=X_face_locations)

    closest_distances = knn_clf.kneighbors(faces_encodings, n_neighbors=1)
    are_matches = [closest_distances[0][i][0] <= distance_threshold for i in range(len(X_face_locations))]

    cv_photo = [(pred, loc) if rec else ("unknown", loc) for pred, loc, rec in zip(knn_clf.predict(faces_encodings),X_face_locations, are_matches)]
    return cv_photo


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'JPG'}


def show_prediction_labels_on_image(frame, predictions):
    pil_image = Image.fromarray(frame)
    draw = ImageDraw.Draw(pil_image)

    for name, (top, right, bottom, left) in predictions:
        top *= 2
        right *= 2
        bottom *= 2
        left *= 2
        
        draw.rectangle(((left, top), (right, bottom)), outline=(0, 0, 255))

        name = name.encode("UTF-8")

        text_width, text_height = draw.textsize(name)
        draw.rectangle(((left, bottom - text_height - 10), (right, bottom)), fill=(0, 0, 255), outline=(0, 0, 255))
        draw.text((left + 6, bottom - text_height - 5), name, fill=(255, 255, 255, 255))

    del draw

    opencvimage = np.array(pil_image)
    return opencvimage


def createImageDir(logger, ip, port):
    folder_name = "public/cams/"+str(ip+":"+port) + "_images0"
    try:
        if not os.path.exists(folder_name):
            os.makedirs(os.path.join(folder_name))
    except OSError as e:
        if e.errno != errno.EEXIST:
            logger.debug("Failed to create " + folder_name + " directory")
            raise


def recvall(sock, count):
    buf = b''
    while count:
        newbuf = sock.recv(count)
        if not newbuf:
            return None
        buf += newbuf
        count -= len(newbuf)
    return buf

def handle(connection, address, ip, port, hostname, mqtt_host, js_port,):
    import logging
    logging.basicConfig(level=logging.DEBUG)
    click_cl = clickhouse_connect.get_client(host='92.53.105.143', port='18123', user='default', password= '')
    logger = logging.getLogger("process-%r" % (address,))
    createImageDir(logger, ip, port)
    cnt = 0
    remote_port = js_port
    folder_num = 0
    try:
        logger.debug("Connected %r at %r", connection, address)
        while True:
            while True:
                if (cnt < 10):
                    cnt_str = '000' + str(cnt)
                elif (cnt < 100):
                    cnt_str = '00' + str(cnt)
                elif (cnt < 1000):
                    cnt_str = '0' + str(cnt)
                else:
                    cnt_str = str(cnt)
                if cnt == 0:
                    startTime = time.localtime()
                cnt += 1

                length = recvall(connection, 64)
                length1 = length.decode('utf-8')
                stringData = recvall(connection, int(length1))
                stime = recvall(connection, 64)
                logger.debug('send time: ' + stime.decode('utf-8'))
                now = time.localtime()
                logger.debug('receive time: ' +
                             datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'))
                data = numpy.frombuffer(
                    base64.b64decode(stringData), numpy.uint8)
                decimg = cv2.imdecode(data, 1)

                img_cv = cv2.resize(decimg, (0, 0), fx=0.5, fy=0.5)
                predictions_label = predict(img_cv, model_path="trained_knn_model.clf")
                logger.info(predictions_label)
                decimg = show_prediction_labels_on_image(decimg, predictions_label)

                data_time = datetime.utcnow()

                time_find_click = str(data_time.strftime('%Y-%m-%d %H:%M:%S'))
                time_find = str(data_time.strftime('%Y-%m-%d_%H:%M:%S.%f'))
                res_people = [who for who, pos in predictions_label]
                res_people = ', '.join(res_people)

                pos = '/cams/' + str(ip+":"+port) + '_images' + str(folder_num) + '/' + time_find + '.jpg'
                
                url_remote = "http://" + hostname + ":" +str(remote_port)+ pos
                #"{\"people\":"+"\""+str(res_people)+"\"," + 
                res = "{\"people\":"+"\""+str(res_people)+"\"," + "\"time\":" +"\""+time_find + "\"," + "\"url\" :" + "\"" + url_remote + "\"}"
                print(res)

                camera_id = "cam/"+str(ip+":"+port)

                publish.single(topic=camera_id, payload=str(res), hostname=mqtt_host)

                cmd = 'INSERT INTO security_db.detection (*) VALUES (\'{}\', \'{}\', \'{}\', \'{}\')'.format(camera_id,res_people, url_remote, time_find_click)
                print(cmd)

                click_cl.command(cmd)

                cv2.imshow("image", decimg)
                cv2.imwrite('./public' + pos, decimg)
                cv2.waitKey(1)
    except:
        logger.exception("Problem handling request")
    finally:
        logger.debug("Closing socket")
        connection.close()


class Server(object):
    def __init__(self, arguments):
        import logging
        self.logger = logging.getLogger("server")
        self.hostname = arguments['--host']
        self.port = int(arguments['--port'])
        self.mqtt_host = arguments['--remote_host']
        self.js_port = int(arguments['--remote_port_web'])

    def start(self):
        self.logger.debug("listening")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.hostname, self.port))
        self.socket.listen(1)
        
        while True:
            conn, address = self.socket.accept()
            self.logger.debug("Got connection")
            ip = str(address[0])
            port = str(address[1])
            process = multiprocessing.Process(
                target=handle, args=(conn, address, ip, port, self.hostname, self.mqtt_host, self.js_port))
            process.daemon = True
            process.start()
            self.logger.debug("Started process %r", process)


if __name__ == "__main__":
    arguments = docopt(help, version='Server (Cameras catcher)')
    import logging
    logging.basicConfig(level=logging.DEBUG)
    server = Server(arguments)
    try:
        logging.info("Listening")
        server.start()
    except:
        logging.exception("Unexpected exception")
    finally:
        logging.info("Shutting down")
        for process in multiprocessing.active_children():
            logging.info("Shutting down process %r", process)
            process.terminate()
            process.join()
    logging.info("All done")