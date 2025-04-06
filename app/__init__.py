from flask import Flask, render_template, request, redirect, url_for, session, flash
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

# Страница профиля
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

# Привязка через Telegram
@app.route('/bind_telegram', methods=['POST'])
def bind_telegram():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    telegram_id = request.form['telegram_id']  # Telegram ID получаем из формы

    # Привязываем Telegram ID к пользователю в базе данных
    user.telegram_id = telegram_id
    db.session.commit()

    flash('Telegram аккаунт привязан успешно!', 'success')
    return redirect(url_for('profile'))


# Страница регистрации
@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'GET':
        return render_template('registration.html')

    username = request.form.get('username')

    if not username:
        flash('Введите имя пользователя')
        return redirect(url_for('registration'))

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        flash('Такой пользователь уже существует')
        return redirect(url_for('registration'))

    new_user = User(username=username)
    db.session.add(new_user)
    db.session.commit()

    session['user_id'] = new_user.id  # Записываем ID пользователя в сессию
    return redirect(url_for('get_projects'))

# Логика регистрации и логина
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        user = User.query.filter_by(username=username).first()

        if not user:
            flash('Пользователь не найден. Пройдите регистрацию.', 'error')
            return redirect(url_for('login'))

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

from flask import jsonify

@app.route('/update_telegram', methods=['POST'])
def update_telegram():
    """Эндпоинт для обновления Telegram ID пользователя."""
    data = request.json
    user_id = data.get('user_id')
    telegram_id = data.get('telegram_id')

    user = db.session.get(User, user_id)  # Новый способ вместо User.query.get(user_id)
    if user:
        user.telegram_id = telegram_id
        db.session.commit()
        return jsonify({"success": True, "message": "Telegram ID успешно обновлен"}), 200
    else:
        return jsonify({"success": False, "message": "Пользователь не найден"}), 404



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
