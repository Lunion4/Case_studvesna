from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import requests
from sqlalchemy.orm import joinedload
from app.bot import send_telegram_message
from flask_login import current_user



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///platform.db'
app.config['SECRET_KEY'] = 'secret_key'
db = SQLAlchemy(app)


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
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='messages')

    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'), nullable=False)

    reply_to_id = db.Column(db.Integer, db.ForeignKey('message.id'))
    reply_to = db.relationship('Message', remote_side=[id])

    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    project = db.relationship('Project', backref='messages')




@app.route('/api/messages/<int:project_id>')
def get_messages_api(project_id):
    chat = Chat.query.filter_by(project_id=project_id).first()
    if not chat:
        return jsonify([])

    messages = db.session.query(Message, User).join(
        User, Message.user_id == User.id
    ).filter(
        Message.chat_id == chat.id
    ).order_by(Message.timestamp).all()

    messages_data = [{
        'id': message.id,
        'username': user.username,
        'content': message.content,
        'timestamp': message.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        'reply_to': {
            'id': message.reply_to.id,
            'username': message.reply_to.user.username,
            'content': message.reply_to.content
        } if message.reply_to else None
    } for message, user in messages]

    return jsonify(messages_data)


@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)


@app.route('/bind_telegram', methods=['POST'])
def bind_telegram():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    telegram_id = request.form['telegram_id']
    user.telegram_id = telegram_id
    db.session.commit()

    flash('Telegram аккаунт привязан успешно!', 'success')
    return redirect(url_for('profile'))


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

    session['user_id'] = new_user.id
    return redirect(url_for('get_projects'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        user = User.query.filter_by(username=username).first()

        if not user:
            flash('Пользователь не найден. Пройдите регистрацию.', 'error')
            return redirect(url_for('login'))

        session['user_id'] = user.id
        return redirect(url_for('get_projects'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))


@app.route('/projects')
def get_projects():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    projects = Project.query.all()
    return render_template('projects.html', projects=projects)


@app.route('/chat/<int:project_id>', methods=['GET', 'POST'])
def chat(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])
    project = db.session.get(Project, project_id)
    if not project:
        return "Проект не найден", 404

    chat = Chat.query.filter_by(project_id=project.id).first()
    if not chat:
        chat = Chat(project_id=project.id)
        db.session.add(chat)
        db.session.commit()

    if request.method == 'POST':
        content = request.form.get('message')
        reply_to_id = request.form.get('reply_to_id')
        if content:
            message = Message(
                content=content,
                timestamp=datetime.utcnow(),
                user_id=user.id,
                chat_id=chat.id,
                reply_to_id=reply_to_id if reply_to_id else None,
                project_id=project.id  # 🔥 Вот эта строка обязательна
            )
            db.session.add(message)
            # Проверяем, является ли это ответом на сообщение
            if reply_to_id:
                replied_message = Message.query.get(reply_to_id)
                if replied_message and replied_message.user and replied_message.user.telegram_id:
                    # Формируем текст уведомления
                    answer_author = user.username
                    notif_text = (
                        f"💬 <b>{answer_author}</b> ответил(а) на ваше сообщение в чате «{project.name}»:\n\n"
                        f"<blockquote>{replied_message.content}</blockquote>\n\n"
                        f"{content}"
                    )
                    # Отправляем уведомление
                    send_telegram_message(replied_message.user.telegram_id, notif_text)

            db.session.commit()
            return redirect(url_for('chat', project_id=project.id))

    messages = Message.query.options(
        joinedload(Message.user),
        joinedload(Message.reply_to)
    ).filter_by(chat_id=chat.id).order_by(Message.timestamp).all()

    messages_data = []
    for msg in messages:
        messages_data.append({
            'id': msg.id,
            'content': msg.content,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'username': msg.user.username if msg.user else 'Unknown',
            'reply_to': {
                'id': msg.reply_to.id,
                'content': msg.reply_to.content,
                'username': msg.reply_to.user.username if msg.reply_to and msg.reply_to.user else 'Unknown'
            } if msg.reply_to else None
        })

    return render_template(
        "chat.html",
        messages=messages_data,
        project_id=project.id,
        project_name=project.name,
        username=user.username
    )


@app.route('/update_telegram', methods=['POST'])
def update_telegram():
    data = request.json
    user_id = data.get('user_id')
    telegram_id = data.get('telegram_id')

    user = db.session.get(User, user_id)
    if user:
        user.telegram_id = telegram_id
        db.session.commit()
        return jsonify({"success": True, "message": "Telegram ID успешно обновлен"}), 200
    else:
        return jsonify({"success": False, "message": "Пользователь не найден"}), 404


@app.route('/chat/<int:project_id>/messages')
def get_new_messages(project_id):
    after_id = request.args.get('after_id', type=int, default=0)
    messages = Message.query.filter(Message.project_id == project_id, Message.id > after_id).order_by(
        Message.timestamp).all()

    def serialize(msg):
        return {
            'id': msg.id,
            'username': msg.user.username,
            'content': msg.content,
            'timestamp': msg.timestamp.strftime('%H:%M:%S'),
            'reply_to': {
                'username': msg.reply_to.user.username,
                'content': msg.reply_to.content[:100]
            } if msg.reply_to else None
        }

    return jsonify([serialize(m) for m in messages])


def send_telegram_notification(telegram_id, message_text):
    TOKEN = ''
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        'chat_id': telegram_id,
        'text': message_text,
        'parse_mode': 'HTML'
    }

    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[Telegram] Ошибка при отправке: {e}")


with app.app_context():
    db.create_all()
    # Заполняем базу примерами
    if not Project.query.first():
        example_projects = [
            Project(name='Биржа гипотез',
                    description='Размещение стартап-идей для реализации другими пользователями.',
                    image_url='https://do.sevsu.ru/pluginfile.php/482908/course/overviewfiles/1.png'),
            Project(name='Центр коллективного пользования',
                    description='Доступ к уникальному оборудованию на коммерческой основе.',
                    image_url='https://habrastorage.org/getpro/habr/upload_files/1dc/025/4b0/1dc0254b0f4c18193f4ffe1ecc42e625.png'),
            Project(name='RnD Market', description='Площадка для получения сервисов для проектов.',
                    image_url='https://smolinvest.ru/upload/iblock/256/256e65eca3e8853df3a5d69c87aaf914.jpg'),
            Project(name='Биржа инвестиций', description='Платформа для связи стартапов с инвесторами.',
                    image_url='https://i.vuzopedia.ru/storage/app/uploads/public/649/b62/020/649b62020fb39722661700.jpeg')
        ]
        db.session.bulk_save_objects(example_projects)
        db.session.commit()
        # Создаем чаты для каждого проекта
        for project in Project.query.all():
            chat = Chat(project_id=project.id)
            db.session.add(chat)
        db.session.commit()
