from datetime import datetime
from flaskblog import db, login_manager
from flask_login import UserMixin
from sqlalchemy.orm import relationship


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(60), unique=True, nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    image_file = db.Column(db.String(60), nullable=True, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False,
                          default=datetime.utcnow)
    events = relationship("Event")
    albums = relationship("Album")

    def __repr__(self):
        return f"User('{self.id}', '{self.name}', '{self.username}', '{self.email}', '{self.phone}', '{self.image_file}', '{self.password}', '{self.role}', '{self.status}', '{self.created_at}', '{self.updated_at}')"


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    eventname = db.Column(db.String(200), unique=False, nullable=False)
    date = db.Column(db.DateTime, nullable=True)
    place = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(1000), nullable=False)
    status = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    slug = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False,
                          default=datetime.utcnow)
    albums = relationship("Album")
    def __repr__(self):
        return f"Event('{self.id}', '{self.eventname}', '{self.place}', '{self.description}', '{self.status}', '{self.slug}', '{self.user_id}', '{self.created_at}', '{self.updated_at}')"


class Album(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    albumname = db.Column(db.String(100), unique=False, nullable=False)
    album_url = db.Column(db.String(200), nullable=False)
    status = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False,
                          default=datetime.utcnow)
    images = relationship("Image")

    def __repr__(self):
        return f"Album('{self.id}', '{self.albumname}', '{self.album_url}', '{self.status}', '{self.user_id}', '{self.event_id}', '{self.created_at}', '{self.updated_at}')"


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    imagename = db.Column(db.String(100), nullable=False)
    image_url = db.Column(db.String(200), nullable=False)
    album_id = db.Column(db.Integer, db.ForeignKey('album.id'), nullable=False)
    status = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False,
                          default=datetime.utcnow)
    features = relationship("Feature")
    bibs = relationship("Bib")

    def __repr__(self):
        return f"Image('{self.id}', '{self.imagename}', '{self.image_url}', '{self.album_id}', '{self.status}', '{self.created_at}', '{self.updated_at}')"


class Feature(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body_coordinate = db.Column(db.String(1000), nullable=True)
    body_feature = db.Column(db.String(2000), nullable=True)
    head_coordinate = db.Column(db.String(1000), nullable=True)
    head_feature = db.Column(db.String(2000), nullable=True)
    upper_coordinate = db.Column(db.String(1000), nullable=True)
    upper_feature = db.Column(db.String(2000), nullable=True)
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False,
                          default=datetime.utcnow)

    def __repr__(self):
        return f"Feature('{self.id}', '{self.body_coordinate}', '{self.body_feature}', '{self.head_coordinate}', '{self.head_feature}', '{self.upper_coordinate}', '{self.upper_feature}', '{self.image_id}', '{self.created_at}', '{self.updated_at}')"


class Bib(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bib_feature = db.Column(db.String(1000), nullable=True)
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False,
                          default=datetime.utcnow)

    def __repr__(self):
        return f"Bib('{self.id}', '{self.bib_feature}', '{self.image_id}', '{self.created_at}', '{self.updated_at}')"
