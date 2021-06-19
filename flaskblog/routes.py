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

app.config['ALLOWED_EXTENSIONS'] = set(
    ['png', 'jpg', 'jpeg'])
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'static', 'uploaded')
IMG_DIR = os.path.join(BASE_DIR, 'static', 'imgs')

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
      x = int(lastpage['href'].split("?page=",1)[1])
      allpaging = []
      for i in range(1,x+1):
        url =  url_input + '?page=%d'%i
        allpaging.append(url)
      for k in range(0,len(allpaging)):
        albums_page = urllib.request.urlopen(allpaging[k])
        soup = soup_page(albums_page)
        albums_list = soup.find_all('h3', attrs={'class': 'product-name'})
        albums_lists = albums_lists + albums_list
    else: 
      albums_lists = find_all_list

    for x in range(0, len(albums_lists)):
      albums_lists[x] = albums_lists[x].find('a')
    for l in albums_lists:
        album = Album(albumname=l['title'], album_url='https://imsports.vn'+l['href'] ,user_id = 1, event_id = 1)
        db.session.add(album)
        db.session.commit()
        flash('Tạo album thành công', 'success')

def load_page(url):
    driver = webdriver.Chrome('/home/tuta/test/crawl/chromedriver',options=sln_options)
    driver.get(url)
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
      driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
      time.sleep(1.0)
      new_height = driver.execute_script("return document.body.scrollHeight")
      if new_height == last_height:
        break
      last_height = new_height
    return driver

def get_link_image():

    albums = Album.query.filter().all()
    for al in albums:
        if al.status == 0:

            photo_page = load_page(al.album_url)
            # Retrieve content of the album
            soup = soup_page(photo_page.page_source)
            photo_list = soup.find_all('div', attrs={'class': 'itemImgGll'})
            k = 0
            for y in range(len(photo_list)):
                img = photo_list[y].find('a')
                k+=1
                image = Image(imagename=al.albumname+' '+str(k), album_id = al.id, image_url = img.get('href'),status = 0)
                db.session.add(image)
            al.status = 1
            db.session.commit()
            flash('Tạo image thành công', 'success')

def bib_predict():
    images = Image.query.filter(Image.album_id == 44).all()
    for image in images:
        image_url = [keras_ocr.tools.read(image.image_url)]
        predictions = pipeline.recognize(image_url)
        for idx, prediction in enumerate(predictions):
            bibs = ''
            for word, array in prediction:
              tmp = re.compile(r"\b[0-9]{1,7}\b|\b[a-z][0-9]{2,}\b").findall(word)
              if (tmp != []):
                bib = tmp.pop()
                bibs = bib +' '+ bibs
        b = Bib(bib_feature=bibs, image_id = image.id)
        db.session.add(b)
        db.session.commit()
    flash('Đọc số BIB thành công', 'success')

@app.route("/bib_predict", methods=['GET', 'POST'])
# @login_required
def predict():
    if request.method == 'POST':
        bib_predict()
    return render_template('admin/bib_predict.html')

@app.route("/", methods=['GET', 'POST'])
@login_required
def home():
    if request.method == "GET":
        if(request.args):
            if "bib" in request.args.keys():
                bib = request.args.get('bib')
                search = "%{}%".format(bib)
                albums = Album.query.filter(Album.event_id == 4).all()
                event = Event.query.filter_by(id = 4).first()
                images = Image.query.join(Bib).filter(Image.album_id.in_([p.id for p in albums]), Bib.bib_feature.like(search)).all()
                count = Image.query.join(Bib).filter(Image.album_id.in_([p.id for p in albums]), Bib.bib_feature.like(search)).count()
                total = Image.query.filter(Image.album_id.in_([p.id for p in albums])).count()
                return render_template('home.html', images=images, event=event, count=count, bib=bib, total=total)
    albums = Album.query.filter(Album.event_id == 4).all()
    images = Image.query.filter(Image.album_id.in_([p.id for p in albums])).all()
    event = Event.query.filter_by(id = 4).first()
    total = Image.query.filter(Image.album_id.in_([p.id for p in albums])).count()
    if request.method == "POST":
        if "img" in request.files:
            uploaded_file = request.files["img"]
            uploaded_file_path = os.path.join(UPLOAD_DIR, uploaded_file.filename)
            uploaded_file.save(uploaded_file_path)
            uploaded_file_path
 
    return render_template('home.html', images=images, event=event,count=total,total=total)

@app.route("/<string:slug>/", methods=['GET', 'POST'])
@login_required
def detail(slug):
    if request.method == "GET":
        if(request.args):
            if "bib" in request.args.keys():
                bib = request.args.get('bib')
                search = "%{}%".format(bib)
                event = Event.query.filter_by(slug = slug).first()
                albums = Album.query.filter(Album.event_id.in_([event.id])).all()
                images = Image.query.join(Bib).filter(Image.album_id.in_([p.id for p in albums]), Bib.bib_feature.like(search)).all()
                count = Image.query.join(Bib).filter(Image.album_id.in_([p.id for p in albums]), Bib.bib_feature.like(search)).count()
                total = Image.query.filter(Image.album_id.in_([p.id for p in albums])).count()
                return render_template('detail.html', images=images, event=event, count=count, bib=bib, total=total,slug=slug)
    page = request.args.get('page', 1, type=int)
    per_page = 40
    event = Event.query.filter_by(slug = slug).first()
    albums = Album.query.filter(Album.event_id.in_([event.id])).all()
    images = Image.query.filter(Image.album_id.in_([p.id for p in albums])).paginate(page,per_page,error_out=False)
    next_url = url_for('detail', slug=slug, page=images.next_num) if images.has_next else None
    prev_url = url_for('detail', slug=slug, page=images.prev_num) if images.has_prev else None
    total = Image.query.filter(Image.album_id.in_([p.id for p in albums])).count()
    if request.method == "POST":
        if "img" in request.files:
            uploaded_file = request.files["img"]
            uploaded_file_path = os.path.join(UPLOAD_DIR, uploaded_file.filename)
            uploaded_file.save(uploaded_file_path)
            uploaded_file_path
 
    return render_template('detail.html', images=images.items, event=event,q=(images.next_num-1)*per_page,total=total,slug=slug,next_url=next_url, prev_url=prev_url)


@app.route("/index1")
@login_required
def index1():
    return render_template('index1.html', title='About')

@app.route("/ajaxfile",methods=["POST","GET"])
def ajaxfile():
    try:
        
        if request.method == 'POST':
            draw = request.form['draw'] 
            row = int(request.form['start'])
            rowperpage = int(request.form['length'])
            searchValue = request.form["search[value]"]
            print(draw)
            print(row)
            print(rowperpage)
            print(searchValue)
 
            ## Total number of records without filtering
            cursor.execute("select count(*) as allcount from employee")
            rsallcount = cursor.fetchone()
            totalRecords = rsallcount['allcount']
            print(totalRecords) 
 
            ## Total number of records with filtering
            likeString = "%" + searchValue +"%"
            cursor.execute("SELECT count(*) as allcount from employee WHERE name LIKE %s OR position LIKE %s OR office LIKE %s", (likeString, likeString, likeString))
            rsallcount = cursor.fetchone()
            totalRecordwithFilter = rsallcount['allcount']
            print(totalRecordwithFilter) 
 
            ## Fetch records
            if searchValue=='':
                cursor.execute("SELECT * FROM employee ORDER BY name asc limit %s, %s;", (row, rowperpage))
                employeelist = cursor.fetchall()
            else:        
                cursor.execute("SELECT * FROM employee WHERE name LIKE %s OR position LIKE %s OR office LIKE %s limit %s, %s;", (likeString, likeString, likeString, row, rowperpage))
                employeelist = cursor.fetchall()
 
            data = []
            for row in employeelist:
                data.append({
                    'name': row['name'],
                    'position': row['position'],
                    'age': row['age'],
                    'salary': row['salary'],
                    'office': row['office'],
                })
 
            response = {
                'draw': draw,
                'iTotalRecords': totalRecords,
                'iTotalDisplayRecords': totalRecordwithFilter,
                'aaData': data,
            }
            return jsonify(response)
    except Exception as e:
        print(e)

@app.route("/events")
def events():
    if request.method == "GET":
        if(request.args):
            if "q" in request.args.keys():
                q = request.args.get('q')
                search = "%{}%".format(q)
                events = Event.query.filter(Event.eventname.like(search) | Event.place.like(search) | Event.description.like(search)).all()
                res = []
                for event in events:
                    album = Album.query.filter(Album.event_id.in_([event.id])).first()
                    image = Image.query.filter(Image.album_id.in_([album.id])).first()
                    r = {
                        'eventname': event.eventname,
                        'date': event.date,
                        'place': event.place,
                        'description': event.description,
                        'image': image.image_url,
                        'slug' : event.slug,
                    }
                    res.append(r)
                return render_template('events.html', title='events', res=res, q=q)
    events = Event.query.filter().all()
    res = []
    for event in events:
        album = Album.query.filter(Album.event_id.in_([event.id])).first()
        image = Image.query.filter(Image.album_id.in_([album.id])).first()
        r = {
            'eventname': event.eventname,
            'date': event.date,
            'place': event.place,
            'description': event.description,
            'image': image.image_url,
            'slug' : event.slug,
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
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route("/create_event", methods=['GET', 'POST'])
# @login_required
def create_event():
    form = EventForm()
    if form.validate_on_submit():
        event = Event(eventname=form.eventname.data,
                    date=form.date.data, place=form.place.data,description=form.description.data,slug=slugify(form.eventname.data))
        db.session.add(event)
        db.session.commit()
        flash('Tạo sự kiện thành công', 'success')
        return redirect(url_for('create_event'))
    return render_template('create_event.html', title='create_event', form=form)

@app.route("/create_album", methods=['GET', 'POST'])
# @login_required
def create_album():
    if request.method == 'POST':
        get_link_album()
    return render_template('admin/create_album.html')

@app.route("/crawl_image", methods=['GET', 'POST'])
# @login_required
def crawl_image():
    if request.method == 'POST':
        get_link_image()
    return render_template('admin/crawl_image.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
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
    return redirect(url_for('home'))

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