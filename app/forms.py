import flask_wtf, wtforms
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

class ProjectForm(FlaskForm):
    name = StringField('Название проекта', validators=[DataRequired(message="Поле не должно быть пустым"), Length(max=100, message='Введите заголовок длиной до 100 символов')])
    description = TextAreaField('Описание проекта', validators=[DataRequired("Поле не должно быть пустым"), Length(max=3000, message='Введите заголовок длиной до 3000 символов')])
    image_url = StringField('Ссылка на изображение', validators=[Optional()])
    submit = SubmitField('Сохранить')