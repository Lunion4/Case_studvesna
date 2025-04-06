from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///platform.db'
app.config['SECRET_KEY'] = 'secret_key'  # Для работы с сессиями
socketio = SocketIO(app, cors_allowed_origins="*")
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
    image_url = db.Column(db.String(255), nullable=True)


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

    # Добавляем связь с User
    user = db.relationship('User', backref='messages')


# Логика регистрации и логина
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()
        session['user_id'] = user.id  # Запоминаем пользователя в сессии
        return redirect(url_for('get_projects'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))


# Роут для получения списка проектов
@app.route('/projects')
def get_projects():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    projects = Project.query.all()
    return render_template('projects.html', projects=projects)


@app.route('/chat/<int:project_id>')
def chat(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('login'))

    # Находим или создаем чат
    chat = Chat.query.filter_by(project_id=project_id).first()
    if not chat:
        chat = Chat(project_id=project_id)
        db.session.add(chat)
        db.session.commit()

    # Получаем сообщения с join'ом пользователей
    messages = db.session.query(Message, User).join(
        User, Message.user_id == User.id
    ).filter(
        Message.chat_id == chat.id
    ).order_by(
        Message.timestamp
    ).all()

    # Подготавливаем данные для шаблона
    messages_data = [{
        'username': user.username,
        'content': message.content,
        'timestamp': str(message.timestamp)
    } for message, user in messages]

    return render_template('chat.html',
                           messages=messages_data,
                           project_id=project_id,
                           username=user.username,
                           user_id=user.id)


# Обработка подключения к чату
@socketio.on('join')
def handle_join(data):
    room = f"chat_{data['project_id']}"
    join_room(room)
    emit('status', {'msg': f"Пользователь {data['username']} присоединился к чату."}, room=room)

    # Отправляем все старые сообщения
    chat = Chat.query.filter_by(project_id=data['project_id']).first()
    if chat:
        messages = [{'username': msg.user.username, 'content': msg.content, 'timestamp': str(msg.timestamp)} for msg in
                    chat.messages]
        emit('load_messages', {'messages': messages}, room=room)


# Обработка отправки сообщений
@socketio.on('send_message')
def handle_send_message(data):
    # Находим чат проекта
    chat = Chat.query.filter_by(project_id=data['project_id']).first()
    if not chat:
        chat = Chat(project_id=data['project_id'])
        db.session.add(chat)
        db.session.commit()

    # Создаем сообщение
    message = Message(
        chat_id=chat.id,
        user_id=data['user_id'],
        content=data['content']
    )
    db.session.add(message)
    db.session.commit()

    # Отправляем в комнату проекта
    room = f"chat_{data['project_id']}"
    emit('new_message', {
        'username': data['username'],
        'content': data['content'],
        'timestamp': str(message.timestamp)
    }, room=room)


with app.app_context():
    db.create_all()
    # Заполняем базу примерами
    if not Project.query.first():
        example_projects = [
            Project(name='Биржа гипотез',
                    description='Размещение стартап-идей для реализации другими пользователями.',
                    image_url='https://source.unsplash.com/400x200/?startup'),
            Project(name='Центр коллективного пользования',
                    description='Доступ к уникальному оборудованию на коммерческой основе.',
                    image_url='https://source.unsplash.com/400x200/?technology'),
            Project(name='RnD Market', description='Площадка для получения сервисов для проектов.',
                    image_url='https://source.unsplash.com/400x200/?business'),
            Project(name='Биржа инвестиций', description='Платформа для связи стартапов с инвесторами.',
                    image_url='https://source.unsplash.com/400x200/?investment')
        ]
        db.session.bulk_save_objects(example_projects)
        db.session.commit()
        # Создаем чаты для каждого проекта
        for project in Project.query.all():
            chat = Chat(project_id=project.id)
            db.session.add(chat)
        db.session.commit()
