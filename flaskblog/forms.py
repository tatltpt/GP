from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from flaskblog.models import User
from wtforms.fields.html5 import DateField


class RegistrationForm(FlaskForm):
    # name = StringField('Họ tên', validators=[DataRequired(), Length(min=2, max=20)])
    username = StringField('Tên đăng nhập', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    # phone = StringField('Điện thoại', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Mật khẩu', validators=[DataRequired()])
    confirm_password = PasswordField('Nhập lại mật khẩu', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Đăng ký')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Tên đăng nhập đã tồn tại. Vui lòng chọn tài khoản khác')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError(
                'Email đã tồn tại. Vui lòng chọn email khác')

class EventForm(FlaskForm):
    eventname = StringField('Tên sự kiện', validators=[DataRequired(), Length(min=2, max=40)])
    date = DateField('Thời gian',format='%d/%m/%Y')
    place = StringField('Địa điểm')
    description = StringField('Mô tả')
    submit = SubmitField('Tạo sự kiện')

class AlbumForm(FlaskForm):
    albumname = StringField('Tên album', validators=[DataRequired()])
    album_url = StringField('Link album')
    submit = SubmitField('Đăng ký')


# class CreateCompany(FlaskForm):
#     name = StringField('Name', validators=[DataRequired(), Length(min=2, max=20)])
#     submit = SubmitField('Create')


# class CreateFormat(FlaskForm):
#     name = StringField('Name', validators=[DataRequired(), Length(min=2, max=20)])
#     url = StringField('URL', validators=[DataRequired(), Length(min=20, max=100)])
#     api = StringField('API', validators=[DataRequired(), Length(min=1, max=100)])
#     description = TextField('Description')
#     company_id = StringField('Company ID')
#     submit = SubmitField('Create')


class LoginForm(FlaskForm):
    username = StringField('Tên đăng nhập', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Mật khẩu', validators=[DataRequired()])
    remember = BooleanField('Lưu đăng nhập')
    submit = SubmitField('Đăng nhập')


class UpdateAccountForm(FlaskForm):
    name = StringField('Họ tên', validators=[DataRequired(), Length(min=2, max=20)])
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])
    phone = StringField('Điện thoại', validators=[DataRequired(), Length(min=2, max=20)])
    submit = SubmitField('Cập nhật')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is taken. Please choose a different one.')
