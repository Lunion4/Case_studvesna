from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///platform.db'
db = SQLAlchemy(app)


# Определение моделей
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    telegram_id = db.Column(db.String(50), unique=True, nullable=True)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(255), nullable=True)  # Добавлено поле для изображения


class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    messages = db.relationship('Message', backref='chat', lazy=True)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# Роут для получения списка проектов
@app.route('/projects')
def get_projects():
    projects = Project.query.all()
    return render_template('projects.html', projects=projects)


# Роут для просмотра чата проекта
@app.route('/chat/<int:project_id>')
def chat(project_id):
    chat = Chat.query.filter_by(project_id=project_id).first()
    messages = chat.messages if chat else []
    return render_template('chat.html', messages=messages, project_id=project_id)


# API для отправки сообщений
@app.route('/chat/send', methods=['POST'])
def send_message():
    data = request.json
    message = Message(chat_id=data['chat_id'], user_id=data['user_id'], content=data['content'])
    db.session.add(message)
    db.session.commit()
    return jsonify({'status': 'success'})


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Заполняем базу примерами
        if not Project.query.first():
            example_projects = [
                Project(name='Биржа гипотез',
                        description='Размещение стартап-идей для реализации другими пользователями.',
                        image_url='https://wotpack.ru/wp-content/uploads/2023/10/word-image-309251-7-750x422.jpeg'),
                Project(name='Центр коллективного пользования',
                        description='Доступ к уникальному оборудованию на коммерческой основе.',
                        image_url='https://wotpack.ru/wp-content/uploads/2023/10/word-image-309251-7-750x422.jpeg'),
                Project(name='RnD Market', description='Площадка для получения сервисов для проектов.',
                        image_url='https://wotpack.ru/wp-content/uploads/2023/10/word-image-309251-9-750x422.jpeg'),
                Project(name='Биржа инвестиций', description='Платформа для связи стартапов с инвесторами.',
                        image_url='https://wotpack.ru/wp-content/uploads/2023/10/word-image-309251-8-750x422.jpeg')
            ]
            db.session.bulk_save_objects(example_projects)
            db.session.commit()

    app.run(debug=True)
