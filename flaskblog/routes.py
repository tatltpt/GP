import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, jsonify, send_file
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
import os
import requests
from selenium import webdriver

app.config['ALLOWED_EXTENSIONS'] = set(
    ['txt', 'pdf', 'png', 'jpg', 'jpeg', 'zip', 'csv', 'tiff'])
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


def create_uuid():
    random.seed(datetime.datetime.now())
    uuid = ''
    for i in range(10):
        uuid += str(random.randint(0, 9))
    return uuid


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


def start_new_thread(function):
    def decorator(*args, **kwargs):
        t = Thread(target=function, args=args, kwargs=kwargs)
        t.daemon = True
        t.start()
        return t

    return decorator


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
    

def update_sql(data):
    formats = Format.query.filter().all()
    for d in data:
        if 'result' in d and d['result'] is not None:
            res = Item.query.filter_by(id=d['id']).first()
            for f in formats:
                if int(d['type']) == f.id:
                    output_image = f.output + d['result']['img'][0]
                    res.output_path = download(output_image)
                    res.result = json.dumps(d['result']['text'][0])
                    res.status = DONE
                    db.session.commit()
        else:
            res = Item.query.filter_by(id=d['id']).first()
            res.status = ERROR
            db.session.commit()


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(
        app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


def zipdir(path, zip):
    for root, dirs, files in os.walk(path):
        for file in files:
            zip.write(os.path.join(root, file))


@start_new_thread
def start_extract(data):
    formats = Format.query.filter().all()
    for d in data:
        try:
            for f in formats:
                if int(d['type']) == f.id:
                    files = {'file': open(os.path.join(
                        UPLOAD_DIR, d['name']), 'rb')}
                    url = f.url + f.api
                    r = requests.post(url, files=files)
                    d['result'] = r.json()
                    break
        except Exception as e:
            print(e)
            d['result'] = None
    update_sql(data)


@app.route("/")
@login_required
def home():
    albums = Album.query.filter(Album.event_id == 4).all()
    images = Image.query.filter(Image.album_id.in_([p.id for p in albums])).all()
    eventname = Event.query.filter_by(id = 4).first()
    count = Image.query.filter(Image.album_id.in_([p.id for p in albums])).count()
    # res = []
    # for data in images:
    #     r = {
    #         'id': data.id,
    #         'image_url': data.image_url,
    #     }
    #     res.append(r)

    # return render_template('bibpix.html', data={'data': res})
    return render_template('bibpix.html', images=images, eventname=eventname, count=count)

@app.route("/about")
@login_required
def about():
    return render_template('about.html', title='About')

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

@app.route("/bibpix")
def bibpix(page_num):
    image = Image.query.paginate(per_page=5, page=page_num, error_out=True)
    return render_template('bibpix.html', title='Bibpix')

@app.route("/races")
def races():
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
        }
        res.append(r)
    return render_template('races.html', title='races', res=res)

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
                    date=form.date.data, place=form.place.data,description=form.description.data)
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
    return render_template('create_album.html')
    # form = AlbumForm()
    # if form.validate_on_submit():
    #     album = Album(albumname=form.albumname.data,
    #                 album_url=form.album_url.data,user_id = 1, event_id = 1)
    #     db.session.add(album)
    #     db.session.commit()
    #     flash('Tạo album thành công', 'success')
    #     return redirect(url_for('create_album'))
    # return render_template('create_album.html', title='create_album', form=form)

@app.route("/crawl_image", methods=['GET', 'POST'])
# @login_required
def crawl_image():
    if request.method == 'POST':
        get_link_image()
    return render_template('crawl_image.html')



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


@app.route("/history", methods=['GET', 'POST'])
@login_required
def history():
    post = Package.query.filter(Package.user_id.in_([current_user.id])).all()
    results = Item.query.filter(Item.post_id.in_([p.id for p in post])).all()
    res = []
    for data in results:
        r = {
            'id': data.id,
            'name': data.name,
            'raw_path': data.raw_path,
            'output_path': data.output_path,
            'type': data.type,
            'result': json.loads(data.result) if data.result is not None else None,
            'status': data.status,
            'correct_result': data.correct_result,
            'view_status': data.view_status,
            'created_at': data.created_at,
        }
        res.append(r)

    return render_template('history.html', data={'data': res})


@app.route("/detail", methods=['GET', 'POST'])
@login_required
def detail():
    post = Package.query.filter(Package.user_id.in_([current_user.id])).all()
    results = Item.query.filter(Item.post_id.in_([p.id for p in post])).all()
    res = []
    for data in results:
        r = {
            'id': data.id,
            'name': data.name,
            'raw_path': data.raw_path,
            'output_path': data.output_path,
            'type': data.type,
            'result': json.loads(data.result) if data.result is not None else None,
            'status': data.status,
            'correct_result': data.correct_result,
            'view_status': data.view_status,
            'created_at': data.created_at,
        }
        res.append(r)
    return render_template('detail.html', data=res)


@app.route("/update_template/<id>")
@login_required
def update_template(id):
    template = SubFormat.query.filter_by(
        company_id=current_user.company_id, id=id).first()
    res = {
        'id': template.id,
        'name': template.name,
        'description': template.description,
        'img_path': template.img_path,
        'company_id': template.company_id,
        'created_at': template.created_at,
    }
    return render_template('update_template.html', data=res)


@app.route("/delete_package", methods=['GET', 'POST'])
@login_required
def delete_package():
    if request.method == 'POST':
        if 'data' in request.form:
            data = request.form['data'].split(',')
            obj = Package.query.filter(Package.id.in_(data)).all()
            for d in obj:
                db.session.delete(d)
            db.session.commit()
            return jsonify({'mess': 'success'})
    return jsonify({'mess': 'failed'}), 400


@app.route("/delete_result", methods=['GET', 'POST'])
@login_required
def delete_result():
    if request.method == 'POST':
        if 'data' in request.form:
            data = request.form['data'].split(',')
            obj = Item.query.filter(Item.id.in_(data)).all()
            for d in obj:
                db.session.delete(d)
            db.session.commit()
            return jsonify({'mess': 'success'})
    return jsonify({'mess': 'failed'}), 400


@app.route("/delete_template", methods=['POST'])
@login_required
def delete_template():
    if request.method == 'POST':
        if 'id' in request.form:
            id = request.form['id']
            id = id.split(',')
            for index in id:
                obj = SubFormat.query.filter_by(id=index).first()
                db.session.delete(obj)
            db.session.commit()
        return jsonify({'mess': 'success'})
    return redirect(url_for('templates'))


@app.route("/duplicate_template", methods=['POST'])
@login_required
def duplicate_template():
    if request.method == 'POST':
        if 'id' in request.form:
            id = request.form['id']
            id = id.split(',')
            # for index in id:
            obj = SubFormat.query.filter_by(id=id).first()
            name = obj.name + ' (COPY)'
            obj = SubFormat(name=name, description=obj.description, img_path=obj.img_path, format_id=obj.format_id,
                            company_id=obj.company_id, created_ip=obj.created_ip, created_user=obj.created_user)
            db.session.add(obj)
            db.session.commit()
            return jsonify({'id': obj.id})
        return jsonify({'mess': 'success'})
    return redirect(url_for('templates'))


@app.route("/rename_template", methods=['POST'])
@login_required
def rename_template():
    if request.method == 'POST':
        if 'id' in request.form:
            id = request.form['id']
            if 'name' in request.form:
                name = request.form['name']
                obj = SubFormat.query.filter_by(id=id).first()
                obj.name = name
                db.session.commit()
        return jsonify({'mess': 'success'})
    return redirect(url_for('templates'))


@app.route("/export", methods=['POST'])
@login_required
def export():
    import xlwt
    if request.method == 'POST':
        if 'data' in request.form:
            data = request.form['data'].split(',')
            obj = Item.query.filter(Item.id.in_(data)).all()
            book = xlwt.Workbook(encoding="utf-8")
            path = datetime.datetime.now().strftime("%Y%m%d_%H%M%S%f") + '.xls'
            for d in obj:
                if d.result is not None:
                    name = d.name
                    if len(d.name) > 30:
                        name = name[:30]
                    sheet = book.add_sheet(name)
                    sheet.write(0, 0, "ID")
                    sheet.write(0, 1, "Text")
                    sheet.write(0, 2, "Probability")
                    i = 1
                    res = json.loads(d.result)
                    for x in res['raw']['result']:
                        sheet.write(i, 0, x['id'])
                        sheet.write(i, 1, x['text'])
                        sheet.write(i, 2, x['prob'])
                        i += 1
            book.save(os.path.join(UPLOAD_DIR, path))
            return jsonify({'path': '/static/uploaded/' + path})


@app.route("/save_export", methods=['POST'])
@login_required
def save_export():
    import xlwt
    if request.method == 'POST':
        if 'id' in request.form:
            # print(data)
            obj = Item.query.filter_by(id=request.form['id']).first()
            book = xlwt.Workbook(encoding="utf-8")
            path = datetime.datetime.now().strftime("%Y%m%d_%H%M%S%f") + '.xls'
            if obj.result is not None:
                name = obj.name
                if len(obj.name) > 30:
                    name = name[:30]
                sheet = book.add_sheet(name)
                sheet.write(0, 0, "ID")
                sheet.write(0, 1, "Text")
                c = 1
                res = json.loads(obj.result)
                for i, x in enumerate(res['raw']['result']):
                    sheet.write(c, 0, i)
                    sheet.write(c, 1, x['text'])
                    c += 1
            book.save(os.path.join(UPLOAD_DIR, path))
            return jsonify({'path': '/static/uploaded/' + path})


@app.route("/save", methods=['POST'])
@login_required
def save_data():
    # import xlwt
    if request.method == 'POST':
        if 'data' in request.form:
            data = request.form['data']
            obj = Item.query.filter_by(id=request.form['id']).first()
            # book = xlwt.Workbook(encoding="utf-8")
            # path = datetime.datetime.now().strftime("%Y%m%d_%H%M%S%f") + '.xls'
            obj.result = data
            db.session.commit()

            return jsonify({'success': True})


@app.route("/exportv2", methods=['POST'])
@login_required
def exportv2():
    if request.method == 'POST':
        if 'data' in request.form:
            obj = Item.query.filter_by(id=request.form['id']).first()
            templates = SubFormat.query.filter(
                company_id=current_user.company_id).all()
            temp = [t.name for t in templates]
            if obj.type in temp:
                path = datetime.datetime.now().strftime("%Y%m%d_%H%M%S%f") + '.csv'
                tmp = None
                for t in templates:
                    if obj.type == t.name:
                        tmp = json.loads(t.description)
                        break
                f = open(os.path.join(UPLOAD_DIR, path), 'w', encoding="utf-8")
                extracted = json.loads(obj.result)['extracted']

                keys = sorted(tmp['results'], key=itemgetter('position'))
                rows = [[d['key'] for d in keys]]
                m = 0
                for x in extracted:
                    merge = []
                    for i in extracted[x]:
                        merge = merge + i
                    extracted[x] = merge
                    if len(extracted[x]) > m:
                        m = len(extracted[x])
                for i in range(m):
                    r = []
                    for x in keys:
                        try:
                            r.append(extracted[x['key']][i])
                        except:
                            r.append('')
                    rows.append(r)
                for row in rows:
                    f.write(','.join(row))
                    f.write('\n')
                return jsonify({'path': '/static/uploaded/' + path})


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


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for(
        'static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account', image_file=image_file, form=form)


@app.route("/update_view_status", methods=['POST'])
@login_required
def update_view_status():
    if request.method == 'POST':
        if 'id' in request.form:
            index = request.form['id']
            obj = Item.query.filter_by(id=index).first()
            obj.view_status = True
            db.session.commit()
        return jsonify({'mess': 'success'})


@app.route("/package/<id>", methods=['GET', 'POST'])
@login_required
def package(id):
    items = Item.query.filter_by(pkg_id=id).all()
    res = []
    for data in items:
        r = {
            'id': data.id,
            'name': data.name,
            'img1': data.image1,
            'img2': data.image2,
            'created_at': data.created_at,
        }
        res.append(r)

    return render_template('package.html', title='Package', data={'data': res})


@app.route("/package/<id>/result", methods=['GET', 'POST'])
@login_required
def result(id):
    items = Item.query.filter_by(pkg_id=id).all()
    res = []
    for data in items:
        r = {
            'id': data.id,
            'name': data.name,
            'img1': data.image1,
            'img2': data.image2,
            'output1': data.output1,
            'output2': data.output2,
            'result': json.loads(data.result) if data.result is not None else None,
            'status': data.status,
            'created_at': data.created_at,
        }
        res.append(r)
    return render_template('result.html', title='Result', data={'data': res})


@app.route("/create_package", methods=['POST'])
@login_required
def create_template():
    if request.method == 'POST':
        if 'name' in request.form:
            name = request.form['name']
            obj = Package(name=name, created_ip=request.remote_addr,
                          user_id=current_user.id)
            db.session.add(obj)
            db.session.commit()
            return jsonify({'id': obj.id})


@app.route("/delete_item", methods=['GET', 'POST'])
@login_required
def delete_item():
    if request.method == 'POST':
        if 'id' in request.form:
            id = request.form['id']
            obj = Item.query.filter_by(id=id).first()
            db.session.delete(obj)
            db.session.commit()
            return jsonify({'mess': 'success'})
    return jsonify({'mess': 'failed'}), 400


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


@app.route("/create_item", methods=['GET', 'POST'])
@login_required
def create_item():
    if request.method == 'POST':
        if 'file1' in request.files and 'file2' in request.files:
            file1 = request.files['file1']
            file2 = request.files['file2']

            if 'name' in request.form:
                name = request.form['name']
                if 'pkg_id' in request.form:
                    pkg_id = request.form['pkg_id']

                    image1 = save_image(file1)
                    image2 = save_image(file2)
                    item = Item(name=name, image1=image1, image2=image2, status=WAITING, pkg_id=pkg_id,
                                created_ip=request.remote_addr)
                    db.session.add(item)
                    db.session.commit()
                    res = {
                        'id': item.id,
                        'name': item.name,
                        'img1': item.image1,
                        'img2': item.image2,
                        'created_at': item.created_at,
                    }
                    return jsonify({'mess': 'success', 'data': res})

    return jsonify({'mess': 'limited'}), 400
