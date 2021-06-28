import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, jsonify
from flaskblog import app, db, bcrypt
from flaskblog.forms import *
from flaskblog.models import *
from flask_login import login_user, current_user, logout_user, login_required
from threading import Thread
import datetime
import requests
import json
import random
import cv2
import numpy as np
from werkzeug.utils import secure_filename
from operator import itemgetter
from sqlalchemy import and_, or_
from bs4 import BeautifulSoup
import urllib
import time
import requests
from selenium import webdriver
import re
import keras_ocr
from slugify import slugify
from tensorflow.keras.applications.vgg16 import VGG16
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.vgg16 import preprocess_input
from keras.layers import Flatten, MaxPooling2D
import h5py
from collections import OrderedDict
import math
import base64
from datetime import datetime

app.config['ALLOWED_EXTENSIONS'] = set(
    ['png', 'jpg', 'jpeg'])
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'static', 'uploaded')
IMG_DIR = os.path.join(BASE_DIR, 'static', 'imgs')
cover_default = '/static/imgs/event-default.jpg'

WAITING = 0
PROCESSING = 1
DONE = 2
ERROR = 3
LIMITED = 4

sln_options = webdriver.ChromeOptions()
sln_options.add_argument('--headless')
sln_options.add_argument('--no-sandbox')
sln_options.add_argument('--disable-dev-shm-usage')

pipeline = keras_ocr.pipeline.Pipeline()

confidence_default = 0.5
threshold = 0.3

# load class labels
labels = open("YOLO/yolo.names").read().strip().split("\n")

# load YOLO weights and configuration file
cfg = "YOLO/yolov4-custom.cfg"
weight = "YOLO/yolov4-custom_last.weights"
# load YOLO detector trained on custom dataset
net = cv2.dnn.readNetFromDarknet(cfg, weight)

# determine the output layer names
l_names = net.getLayerNames()
ol_names = [l_names[i[0]-1] for i in net.getUnconnectedOutLayers()]


def detect_img(img):
    image_r = img
    (H, W) = image_r.shape[:2]

    # construct a blob from the input image, pass to the YOLO detector and
    # grab the bounding boxes and associated probabilities
    blob = cv2.dnn.blobFromImage(
        image_r, 1/255.0, (416, 416), swapRB=True, crop=False)
    net.setInput(blob)
    layer_outputs = net.forward(ol_names)

    # initialize some output lists
    boxes = []
    confidences = []
    classIDs = []

    # output of YOLO [0:4]: [center_x, center_y, box_w, box_h]
    # output of YOLO [4]: confidence
    # output of YOLO [5:]: class scores
    for output in layer_outputs:
        for detection in output:
            scores = detection[5:]
            classID = np.argmax(scores)
            confidence = scores[classID]

            if confidence > confidence_default:
                (center_x, center_y, width, height) = (
                    detection[0:4] * ([W, H, W, H])).astype("int")
                x = int(center_x - (width/2))
                y = int(center_y - (height/2))
                if x < 0:
                    width = width - x
                    x = 0
                if y < 0:
                    height = height - y
                    y = 0
                boxes.append([x, y, int(width), int(height)])
                confidences.append(float(confidence))
                classIDs.append(classID)
    idxs = cv2.dnn.NMSBoxes(boxes, confidences, confidence_default, threshold)
    return boxes, confidences, classIDs, idxs


def cut_boxes(img, x, y, w, h):
    cuted = img[y:y+h, x:x+w]
    return cuted


def check_arr(str, str1):
    a = []
    for i in range(len(str)):
        for j in range(len(str1)):
            if str1[j] == str[i]:
                a.append(str1[j])
    return a


def get_feature(img):
    model = VGG16(weights='imagenet', include_top=False)

    img_resized = cv2.resize(src=img, dsize=(224, 224))
    #img_f = image.load_img(img, target_size=(224, 224))
    x = image.img_to_array(img_resized)
    x = np.expand_dims(x, axis=0)
    x = preprocess_input(x)

    features = model.predict(x)

    max_pool_2d = MaxPooling2D(pool_size=(2, 2), strides=(2, 2))
    features = max_pool_2d(features)
    features = Flatten()(features)
    return features


def load_features(file_name):
    f = h5py.File(file_name, 'r')
    features = f['features'][:]
    image_paths = f['image_paths']

    return features, image_paths


def index_annoy(features, file_name):
    from annoy import AnnoyIndex
    f = len(features[0][0])
    t = AnnoyIndex(f, 'angular')  # Length of item vector that will be indexed
    for i in range(len(features)):
        v = features[i][0]
        t.add_item(i, v)

    t.build(10)  # 10 trees
    t.save(file_name)


def search_feature(input_file):
    from annoy import AnnoyIndex
    features, image_paths = load_features(file_name='face.h5')
    features2, image_paths2 = load_features(file_name='body.h5')
    print(len(features))

    input_f = h5py.File(input_file, 'r')
    features_arr = input_f['features'][:]
    class_arr = input_f['labels']

    label = str(class_arr[0])[2:len(str(class_arr[0]))-1]
    print(label)

    f = len(features_arr[0][0])
    face = AnnoyIndex(f, 'angular')
    body = AnnoyIndex(f, 'angular')
    face.load('face.ann')  # super fast, will just mmap the file
    body.load('body.ann')

    images_all = []
    images_face = []
    images_body = []
    print('lay 10 chi muc', face.get_nns_by_item(0, 10))
    print('features_arr', len(features_arr))
    for i in range(len(features_arr)):
        imgs = []
        label = str(class_arr[i])[2:len(str(class_arr[i]))-1]
        if label == 'face':
            # will find the 1000 nearest neighbors
            print("lay 10 chi muc", face.get_nns_by_vector(
                features_arr[i][0], 10))
            index_img, inclu = face.get_nns_by_vector(
                features_arr[i][0], 10, include_distances=True)
            print("khoang cách", inclu)
            for i in range(len(inclu)):
                if inclu[i] < 0.8:
                    print(index_img[i])
                    path = str(image_paths[index_img[i]])[
                        2:len(str(image_paths[index_img[i]]))-1]
                    imgs.append(path)
            imgs = list(OrderedDict.fromkeys(imgs))
            images_face = images_face + imgs
            images_face = list(OrderedDict.fromkeys(images_face))
            print("so anh face", images_face)

        if label == 'body':
            # will find the 1000 nearest neighbors
            print("lay 10 chi muc", body.get_nns_by_vector(
                features_arr[i][0], 10))
            index_img, inclu = body.get_nns_by_vector(
                features_arr[i][0], 10, include_distances=True)
            print("khoang cách", inclu)
            for i in range(len(inclu)):
                if inclu[i] < 0.8:
                    print(index_img[i])
                    path = str(image_paths[index_img[i]])[
                        2:len(str(image_paths[index_img[i]]))-1]
                    imgs.append(path)
            imgs = list(OrderedDict.fromkeys(imgs))
            images_body = images_body + imgs
            images_body = list(OrderedDict.fromkeys(images_body))
            print("so anh body", images_body)

    images_all = images_face + images_body
    images_all = list(OrderedDict.fromkeys(images_all))
    images = check_arr(images_body, images_face)
    print("dong 356", images_all)
    print("images", images)
    return images, images_all


def search_image(path):
    input_i = cv2.imread(path)
    boxes, confidences, classIDs, idxs = detect_img(input_i)
    indexs = []
    indexs_all = []
    if len(idxs) > 0:
        features_arr = []
        class_arr = []
        for i in idxs.flatten():
            if (labels[classIDs[i]] == 'face' or labels[classIDs[i]] == 'body'):
                (x, y) = (boxes[i][0], boxes[i][1])
                (w, h) = (boxes[i][2], boxes[i][3])
                box = cut_boxes(input_i, x, y, w, h)
                fe = get_feature(box)
                features_arr.append(fe)
                class_arr.append(labels[classIDs[i]])
                print(labels[classIDs[i]])
            else:
                continue
    with h5py.File('feature.h5',  "a") as f:
        if list(f.keys()) != []:
            if list(f.keys())[0] == 'features' and list(f.keys())[1] == 'labels':
                del f['features']
                del f['labels']
        f.create_dataset('features', data=features_arr)
        f.create_dataset('labels', data=class_arr)

    f = h5py.File('feature.h5', 'r')
    features_arr = f['features'][:]
    indexs, indexs_all = search_feature(input_file='feature.h5')

    return indexs, indexs_all, len(features_arr)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


def download(url):
    try:
        get_response = requests.get(url, stream=True, verify=False, timeout=5)
        if get_response.status_code == 200:
            file_name = url.split("/")[-1]
            path = os.path.join(UPLOAD_DIR, file_name)
            with open(path, 'wb') as f:
                for chunk in get_response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
        else:
            file_name = None
    except:
        file_name = None
    return file_name


def soup_page(page):
    try:
        return BeautifulSoup(page, 'lxml')
    except:
        print("Cannot fetch the requested page")


def get_link_album():

    # Open album page
    url_input = 'https://imsports.vn/giai-chay-nam-2021-ac1925.html'
    albums_page = urllib.request.urlopen(url_input)
    soup = soup_page(albums_page)
    # Locate albums section and retrieve all album links
    lastpage = soup.find('a', attrs={'class': 'paging-last'})
    find_all_list = soup.find_all('h3', attrs={'class': 'product-name'})
    albums_lists = []
    if lastpage != []:
        x = int(lastpage['href'].split("?page=", 1)[1])
        allpaging = []
        for i in range(1, x+1):
            url = url_input + '?page=%d' % i
            allpaging.append(url)
        for k in range(0, len(allpaging)):
            albums_page = urllib.request.urlopen(allpaging[k])
            soup = soup_page(albums_page)
            albums_list = soup.find_all('h3', attrs={'class': 'product-name'})
            albums_lists = albums_lists + albums_list
    else:
        albums_lists = find_all_list

    for x in range(0, len(albums_lists)):
        albums_lists[x] = albums_lists[x].find('a')
    for l in albums_lists:
        album = Album(
            albumname=l['title'], album_url='https://imsports.vn'+l['href'], user_id=1, event_id=1)
        db.session.add(album)
        db.session.commit()
        flash('Tạo album thành công', 'success')


def load_page(url):
    driver = webdriver.Chrome(
        '/home/tuta/test/crawl/chromedriver', options=sln_options)
    driver.get(url)
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.0)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    return driver


def get_link_image(id):
    album = Album.query.filter(Album.id == id).first()
    photo_page = load_page(album.album_url)
    # Retrieve content of the album
    soup = soup_page(photo_page.page_source)
    photo_list = soup.find_all('div', attrs={'class': 'itemImgGll'})
    k = 0
    for y in range(len(photo_list)):
        img = photo_list[y].find('a')
        k += 1
        image = Image(imagename=album.albumname+' '+str(k),
                      album_id=album.id, image_url=img.get('href'), status=0)
        db.session.add(image)
    db.session.commit()
    flash('Crawl image thành công', 'success')


@app.route("/crawl_image/<id>", methods=['GET', 'POST'])
def crawl_image(id):
    if request.method == 'POST':
        album = Album.query.filter_by(id=id).first()
        get_link_image(album.id)
        album.status = 1
        db.session.commit()
        return redirect(url_for('show_list'))


@app.route("/crawl_album", methods=['GET', 'POST'])
@login_required
def crawl_album():
    if request.method == 'POST':
        get_link_album()
    return render_template('admin/crawl_album.html')


def bib_predict(id):
    images = Image.query.filter(Image.album_id == id).all()
    for image in images:
        if bool(Bib.query.filter_by(image_id=image.id).first()) == False:
            image_url = [keras_ocr.tools.read(image.image_url)]
            predictions = pipeline.recognize(image_url)
            for idx, prediction in enumerate(predictions):
                bibs = ''
                for word, array in prediction:
                    tmp = re.compile(
                        r"\b[0-9]{1,7}\b|\b[a-z][0-9]{2,}\b").findall(word)
                    if (tmp != []):
                        bib = tmp.pop()
                        bibs = bib + ' ' + bibs
            b = Bib(bib_feature=bibs, image_id=image.id)
            db.session.add(b)
            image.status = 1
            db.session.commit()
    flash('Đọc số BIB thành công', 'success')

# @app.route("/bib_predict", methods=['GET', 'POST'])
# # @login_required
# def predict():
#     if request.method == 'POST':
#         bib_predict()
#     return render_template('admin/bib_predict.html')


def save_features_img(id):
    features_face = []
    face_paths = []
    features_body = []
    body_paths = []
    images = Image.query.filter(Image.album_id == id).all()
    for image in images:
        print(image.image_url)
        resp = urllib.request.urlopen(image.image_url)
        img = np.asarray(bytearray(resp.read()), dtype="uint8")
        img = cv2.imdecode(img, cv2.IMREAD_COLOR)
        boxes, confidences, classIDs, idxs = detect_img(img)
        if len(idxs) > 0:
            for i in idxs.flatten():
                if (labels[classIDs[i]] == 'face'):
                    (x, y) = (boxes[i][0], boxes[i][1])
                    (w, h) = (boxes[i][2], boxes[i][3])
                    box = cut_boxes(img, x, y, w, h)
                    fe = get_feature(box)
                    features_face.append(fe)
                    face_paths.append(image.image_url)
                if (labels[classIDs[i]] == 'body'):
                    (x, y) = (boxes[i][0], boxes[i][1])
                    (w, h) = (boxes[i][2], boxes[i][3])
                    box = cut_boxes(img, x, y, w, h)
                    fe = get_feature(box)
                    features_body.append(fe)
                    body_paths.append(image.image_url)
                else:
                    continue
        with h5py.File('face.h5',  "a") as f:
            if list(f.keys()) != []:
                if list(f.keys())[0] == 'features' and list(f.keys())[1] == 'image_paths':
                    del f['features']
                    del f['image_paths']
            f.create_dataset('features', data=features_face)
            f.create_dataset('image_paths', data=face_paths)
            f.close()

        with h5py.File('body.h5',  "a") as f:
            if list(f.keys()) != []:
                if list(f.keys())[0] == 'features' and list(f.keys())[1] == 'image_paths':
                    del f['features']
                    del f['image_paths']
            f.create_dataset('features', data=features_body)
            f.create_dataset('image_paths', data=body_paths)
            f.close()
        features, image_paths = load_features(file_name='face.h5')
        features2, image_paths2 = load_features(file_name='body.h5')
        print(features[9])
        print('path', image_paths[9])
        index_annoy(features, file_name='face.ann')
        index_annoy(features2, file_name='body.ann')
    flash('Lấy đặc trưng thành công', 'success')


@app.route("/album_manager", methods=['GET', 'POST'])
@login_required
def show_list():
    if request.method == 'GET':
        albums = Album.query.filter().order_by(Album.id.desc())
        users = User.query.filter().all()
    return render_template('admin/album_manager.html', albums=albums, users=users)


@app.route("/bib_predict/<id>", methods=['GET', 'POST'])
def predict(id):
    if request.method == 'POST':
        album = Album.query.filter_by(id=id).first()
        bib_predict(album.id)
        if album.status == 1:
            album.status = 2
        else:
            album.status = 4
        db.session.commit()
        return redirect(url_for('show_list'))


@app.route("/get_feature/<id>", methods=['GET', 'POST'])
def getFeatures(id):
    if request.method == 'POST':
        album = Album.query.filter_by(id=id).first()
        save_features_img(album.id)
        if album.status == 1:
            album.status = 3
        else:
            album.status = 4
        db.session.commit()
        return redirect(url_for('show_list'))

@app.route("/lock/<id>", methods=['GET', 'POST'])
def lock(id):
    if request.method == 'POST':
        user = User.query.filter_by(id=id).first()
        
        if user.status == 1:
            user.status = 0
        else:
            user.status = 1
        db.session.commit()
        return redirect(url_for('show_list'))

@app.route("/get_feature", methods=['GET', 'POST'])
# @login_required
def save_feature():
    if request.method == 'POST':
        albums = Album.query.filter(Album.id == 44).all()
        features_face = []
        face_paths = []
        features_body = []
        body_paths = []
        for album in albums:
            images = Image.query.filter(Image.album_id == album.id).all()
            for image in images:
                print(image.image_url)
                resp = urllib.request.urlopen(image.image_url)
                img = np.asarray(bytearray(resp.read()), dtype="uint8")
                img = cv2.imdecode(img, cv2.IMREAD_COLOR)
                boxes, confidences, classIDs, idxs = detect_img(img)
                if len(idxs) > 0:
                    for i in idxs.flatten():
                        if (labels[classIDs[i]] == 'face'):
                            (x, y) = (boxes[i][0], boxes[i][1])
                            (w, h) = (boxes[i][2], boxes[i][3])
                            box = cut_boxes(img, x, y, w, h)
                            fe = get_feature(box)
                            features_face.append(fe)
                            face_paths.append(image.image_url)
                        if (labels[classIDs[i]] == 'body'):
                            (x, y) = (boxes[i][0], boxes[i][1])
                            (w, h) = (boxes[i][2], boxes[i][3])
                            box = cut_boxes(img, x, y, w, h)
                            fe = get_feature(box)
                            features_body.append(fe)
                            body_paths.append(image.image_url)
                        else:
                            continue
        with h5py.File('face.h5',  "a") as f:
            if list(f.keys()) != []:
                if list(f.keys())[0] == 'features' and list(f.keys())[1] == 'image_paths':
                    del f['features']
                    del f['image_paths']
            f.create_dataset('features', data=features_face)
            f.create_dataset('image_paths', data=face_paths)
            f.close()

        with h5py.File('body.h5',  "a") as f:
            if list(f.keys()) != []:
                if list(f.keys())[0] == 'features' and list(f.keys())[1] == 'image_paths':
                    del f['features']
                    del f['image_paths']
            f.create_dataset('features', data=features_body)
            f.create_dataset('image_paths', data=body_paths)
            f.close()
        features, image_paths = load_features(file_name='face.h5')
        features2, image_paths2 = load_features(file_name='body.h5')
        print(features[9])
        print('path', image_paths[9])
        index_annoy(features, file_name='face.ann')
        index_annoy(features2, file_name='body.ann')
    return render_template('admin/get_feature.html')


# @app.route("/", methods=['GET', 'POST'])
# @login_required
# def home():
#     if request.method == "GET":
#         if(request.args):
#             if "bib" in request.args.keys():
#                 bib = request.args.get('bib')
#                 search = "%{}%".format(bib)
#                 albums = Album.query.filter(Album.event_id == 4).all()
#                 event = Event.query.filter_by(id=4).first()
#                 images = Image.query.join(Bib).filter(Image.album_id.in_(
#                     [p.id for p in albums]), Bib.bib_feature.like(search)).all()
#                 count = Image.query.join(Bib).filter(Image.album_id.in_(
#                     [p.id for p in albums]), Bib.bib_feature.like(search)).count()
#                 total = Image.query.filter(
#                     Image.album_id.in_([p.id for p in albums])).count()
#                 return render_template('home.html', images=images, event=event, count=count, bib=bib, total=total)
#     albums = Album.query.filter(Album.event_id == 4).all()
#     images = Image.query.filter(
#         Image.album_id.in_([p.id for p in albums])).all()
#     event = Event.query.filter_by(id=4).first()
#     total = Image.query.filter(
#         Image.album_id.in_([p.id for p in albums])).count()
#     if request.method == "POST":
#         if "img" in request.files:
#             uploaded_file = request.files["img"]
#             uploaded_file_path = os.path.join(
#                 UPLOAD_DIR, uploaded_file.filename)
#             uploaded_file.save(uploaded_file_path)
#             uploaded_file_path

#     return render_template('home.html', images=images, event=event, count=total, total=total)


@app.route("/events/<string:slug>/", methods=['GET', 'POST'])
def detail(slug):
    if request.method == "GET":
        if(request.args):
            if "bib" in request.args.keys():
                bib = request.args.get('bib')
                search = "%{}%".format(bib)
                event = Event.query.filter_by(slug=slug).first()
                albums = Album.query.filter(
                    Album.event_id.in_([event.id])).all()
                images = Image.query.join(Bib).filter(Image.album_id.in_(
                    [p.id for p in albums]), Bib.bib_feature.like(search)).all()
                count = Image.query.join(Bib).filter(Image.album_id.in_(
                    [p.id for p in albums]), Bib.bib_feature.like(search)).count()
                total = Image.query.filter(
                    Image.album_id.in_([p.id for p in albums])).count()
                item = count
                check = 0
                return render_template('detail.html', images=images, event=event, count=count, bib=bib, total=total, slug=slug, item=item, check=check)
    page = request.args.get('page', 1, type=int)
    per_page = 40
    event = Event.query.filter_by(slug=slug).first()
    albums = Album.query.filter(Album.event_id.in_([event.id])).all()
    print('album', albums)
    if albums == []:
        return render_template('empty.html', event=event)
    images = Image.query.filter(Image.album_id.in_(
        [p.id for p in albums])).paginate(page, per_page, error_out=False)
    next_url = url_for('detail', slug=slug,
                       page=images.next_num) if images.has_next else None
    prev_url = url_for('detail', slug=slug,
                       page=images.prev_num) if images.has_prev else None
    total = Image.query.filter(
        Image.album_id.in_([p.id for p in albums])).count()

    indexs = []
    indexs_all = []
    if request.method == "POST":
        if "img" in request.files:
            st = time.time()
            uploaded_file = request.files["img"]
            uploaded_file_path = os.path.join(
                UPLOAD_DIR, uploaded_file.filename)
            print("uploaded_file_path", uploaded_file_path)
            uploaded_file.save(uploaded_file_path)
            print(uploaded_file_path)
            indexs, indexs_all, f = search_image(uploaded_file_path)
            end = time.time()
            len1 = len(indexs)
            len2 = len(indexs_all)
            t = end - st
            check = 1
            return render_template('detail.html', indexs=indexs, indexs_all=indexs_all, len1=len1, len2=len2, t=t, f=f, images=images.items, event=event, q=(images.next_num-1)*per_page, total=total, slug=slug, check=check, next_url=next_url,    prev_url=prev_url)
    # if request.method == "POST":
    #     if "img" in request.files:
    #         uploaded_file = request.files["img"]
    #         uploaded_file_path = os.path.join(
    #             UPLOAD_DIR, uploaded_file.filename)
    #         uploaded_file.save(uploaded_file_path)
    #         uploaded_file_path
    count = 0
    check = 0
    return render_template('detail.html', images=images.items, event=event, q=(images.next_num-1)*per_page, total=total, slug=slug, next_url=next_url, prev_url=prev_url, count=count, indexs_all=indexs_all, check=check)


@app.route("/", methods=['GET', 'POST'])
@app.route("/events")
# @login_required
def events():

    if request.method == "GET":
        if(request.args):
            if "q" in request.args.keys():
                q = request.args.get('q')
                search = "%{}%".format(q)
                events = Event.query.filter(Event.eventname.like(search) | Event.place.like(
                    search) | Event.description.like(search)).all()
                res = []
                for event in events:
                    if Album.query.filter(Album.event_id.in_([event.id])).first():
                        image = Image.query.filter(
                            Image.album_id.in_([Album.query.filter(Album.event_id.in_([event.id])).first().id])).first()
                        event.cover_img = image.image_url
                        db.session.commit()
                    r = {
                        'eventname': event.eventname,
                        'date': event.date,
                        'place': event.place,
                        'description': event.description,
                        'image': event.cover_img,
                        'slug': event.slug,
                        'user_id': event.user_id
                    }
                    res.append(r)
                return render_template('events.html', title='events', res=res, q=q)
    events = Event.query.filter().all()
    res = []
    for event in events:
        if Album.query.filter(Album.event_id.in_([event.id])).first():
            image = Image.query.filter(
                Image.album_id.in_([Album.query.filter(Album.event_id.in_([event.id])).first().id])).first()
            event.cover_img = image.image_url
            db.session.commit()
        r = {
            'eventname': event.eventname,
            'date': event.date,
            'place': event.place,
            'description': event.description,
            'image': event.cover_img,
            'slug': event.slug,
            'user_id': event.user_id
        }
        res.append(r)
    return render_template('events.html', title='events', res=res)


@app.route("/events_user")
@login_required
def events_user():
    if request.method == "GET":
        if(request.args):
            if "q" in request.args.keys():
                q = request.args.get('q')
                search = "%{}%".format(q)
                events = Event.query.filter(and_(Event.user_id == current_user.id, or_(Event.eventname.like(search), Event.place.like(
                    search), Event.description.like(search)))).all()
                res = []
                for event in events:
                    if Album.query.filter(Album.event_id.in_([event.id])).first():
                        image = Image.query.filter(
                            Image.album_id.in_([Album.query.filter(Album.event_id.in_([event.id])).first().id])).first()
                        event.cover_img = image.image_url
                        db.session.commit()
                    r = {
                        'eventname': event.eventname,
                        'date': event.date,
                        'place': event.place,
                        'description': event.description,
                        'image': event.cover_img,
                        'slug': event.slug,
                        'user_id': event.user_id
                    }
                    res.append(r)
                return render_template('events.html', title='events', res=res, q=q)
    events = Event.query.filter(Event.user_id == current_user.id).all()
    res = []
    for event in events:
        if Album.query.filter(Album.event_id.in_([event.id])).first():
            image = Image.query.filter(
                Image.album_id.in_([Album.query.filter(Album.event_id.in_([event.id])).first().id])).first()
            event.cover_img = image.image_url
            db.session.commit()
        r = {
            'eventname': event.eventname,
            'date': event.date,
            'place': event.place,
            'description': event.description,
            'image': event.cover_img,
            'slug': event.slug,
            'user_id': event.user_id
        }
        res.append(r)
    return render_template('events.html', title='events', res=res)


@app.route("/profile")
@login_required
def profile():
    data = {
        'user_id': current_user.id,
        'created_at': current_user.created_at
    }
    return render_template('profile.html', title='profile', data=data)


@app.route("/register", methods=['GET', 'POST'])
# @login_required
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(
            form.password.data).decode('utf-8')
        user = User(username=form.username.data,
                    email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Tạo tài khoản thành công.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/create_event", methods=['GET', 'POST'])
@login_required
def create_event():
    form = EventForm()
    if form.validate_on_submit():

        event = Event(eventname=form.eventname.data, date=form.date.data, place=form.place.data,
                      description=form.description.data, slug=slugify(form.eventname.data), status=0, user_id=current_user.id, cover_img=cover_default)
        db.session.add(event)
        db.session.commit()
        flash('Tạo sự kiện thành công', 'success')
        return redirect(url_for('create_event'))

    return render_template('create_event.html', title='create_event', form=form)


@app.route("/update_event/<string:slug>/", methods=['GET', 'POST'])
@login_required
def update_event(slug):
    form = EventFormUpdate()
    event = Event.query.filter_by(slug=slug).first()
    form.eventname.data = event.eventname
    form.date.data = event.date
    form.place.data = event.place
    form.description.data = event.description
    if form.validate_on_submit():
        event.eventname = request.form['eventname']
        event.place = request.form['place']
        event.description = request.form['description']
        date = datetime.strptime(request.form['date'], '%d-%m-%Y')
        event.date = date
        db.session.commit()
        flash('Sửa sự kiện thành công', 'success')
        return redirect(url_for('events'))

    return render_template('update_event.html', title='upload_event', form=form)


@app.route("/delete_event/<string:slug>/", methods=['GET', 'POST'])
@login_required
def delete_event(slug):
    if request.method == 'POST':
        event = Event.query.filter_by(slug=slug).first()
        db.session.delete(event)
        db.session.commit()
        flash('Xóa sự kiện thành công', 'success')
        return redirect(url_for('events'))
    return redirect(url_for('events'))


@app.route("/create_album", methods=['GET', 'POST'])
@login_required
def create_album():
    form = AlbumForm()
    if form.validate_on_submit():
        event = Event.query.filter_by(
            eventname=form.event.data.eventname).first()
        album = Album(event_id=event.id, albumname=form.albumname.data,
                      album_url=form.album_url.data, user_id=current_user.id, status=0)
        db.session.add(album)
        db.session.commit()
        flash('Thêm đường dẫn thành công. Chờ quản trị viên xử lý', 'success')
        return redirect(url_for('create_album'))
    return render_template('create_album.html', title='create_album', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('events'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('events'))
        else:
            flash(
                'Đăng nhập thất bại. Vui lòng kiểm tra lại tên đăng nhập, mật khẩu', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/update_pass", methods=['POST'])
@login_required
def update_pass():
    if request.method == 'POST':
        if 'pass' in request.form:
            data = request.form['pass']
            user = User.query.filter_by(id=current_user.id).first()
            user.password = bcrypt.generate_password_hash(data).decode('utf-8')
            db.session.commit()
    return redirect(url_for('profile'))


@app.route("/update_infor", methods=['POST'])
@login_required
def update_infor():
    if request.method == 'POST':
        if 'name' in request.form:
            data = request.form['name']
            user = User.query.filter_by(id=current_user.id).first()
            user.name = data
            db.session.commit()
    return redirect(url_for('profile'))


@app.route("/update_avatar", methods=['POST'])
@login_required
def update_avatar():
    if request.method == 'POST':
        if 'avatar' in request.files:
            file = request.files['avatar']
            filename = secure_filename(file.filename)
            file.save(os.path.join(IMG_DIR, filename))
            user = User.query.filter_by(id=current_user.id).first()
            user.image_file = filename
            db.session.commit()
    return redirect(url_for('profile'))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('events'))


def save_image(file):
    path = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + '_' + \
        str(random.randint(1000, 9999)) + '.png'
    if file.filename.lower().endswith('.pdf'):
        pages = convert_from_bytes(file.read())
        img = np.array(pages[0])
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    else:
        img = np.fromstring(file.read(), np.uint8)
        img = cv2.imdecode(img, cv2.COLOR_RGB2BGR)
    cv2.imwrite(os.path.join(UPLOAD_DIR, path), img)
    return path
