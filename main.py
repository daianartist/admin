from flask import Flask, render_template, url_for, request, session, redirect, g, abort, flash, jsonify, send_file, Blueprint, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import psycopg2
from FDATABASE import FDATABASE
import os
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import qrcode
import jwt
from datetime import datetime, timedelta

DEBUG = True
SECRET_KEY = 'DBLFKJADSBCBALIasfGSGDSDHgdf6EF&ADL@E3213IL>SBBFL'

app = Flask(__name__)
upload_folder = os.path.join('static', 'uploads')
app.config['UPLOAD'] = upload_folder
app.config.from_object(__name__)

# Создание Blueprint для API
api_bp = Blueprint('api', __name__)

# Определение маршрутов Blueprint **до** его регистрации
@api_bp.route('/test', methods=['GET'])
def test_api():
    return jsonify({"message": "API is working"}), 200
@api_bp.route('/user/<string:uin>', methods=['GET']) 
def get_user_by_uin(uin): 
    # Получаем заголовок Authorization 
    auth_header = request.headers.get('Authorization', None) 
    if not auth_header: 
        return jsonify({"error": "Authorization header missing"}), 401 
     
    # Проверяем формат заголовка Authorization 
    parts = auth_header.split() 
    if len(parts) != 2 or parts[0].lower() != 'bearer': 
        return jsonify({"error": "Invalid Authorization header format"}), 401 
     
    token = parts[1] 
     
    try: 
        # Декодируем JWT-токен 
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"]) 
    except jwt.ExpiredSignatureError: 
        return jsonify({"error": "Token expired"}), 401 
    except jwt.InvalidTokenError: 
        return jsonify({"error": "Invalid token"}), 401 
 
    # Получаем соединение с БД 
    db = get_db() 
    dbase = FDATABASE(db) 
     
    # Получаем пользователя по UIN 
    user = dbase.get_user_by_uin(uin) 
    if not user: 
        return jsonify({"error": "User not found"}), 404 
 
    # Формируем ответ без поля 'password' для безопасности 
    user_data = { 
        "role": user.get('role'), 
        "last_name": user.get('last_name'), 
        "first_name": user.get('first_name'), 
        "patronymic": user.get('patronymic'), 
        "uin": user.get('uin'), 
        "email": user.get('email'), 
        "phone_number": user.get('phone_number'), 
        "id_card": user.get('id_card'), 
        "group": user.get('group') 
    } 
 
    return jsonify(user_data), 200
# @api_bp.route('/login_by_uin', methods=['POST'])
# def login_by_uin():
#     db = get_db()
#     dbase = FDATABASE(db)
#     data = request.get_json()
#     if not data:
#         return jsonify({"error": "No JSON body provided"}), 400
#     uin = data.get('uin')
#     password = data.get('password')
#     if not all([uin, password]):
#         return jsonify({"error": "Please provide UIN and password"}), 400

#     user = dbase.get_user_by_uin(uin)
#     if user and check_password_hash(user['password'], password):
#         return jsonify({
#             "success": True,
#             "user_id": user['id'],
#             "user_role": user['role'],
#             "message": "Login by UIN successful"
#         }), 200
#     else:
#         return jsonify({"error": "Invalid UIN or password"}), 401
@api_bp.route('/login_by_uin', methods=['POST'])
def login_by_uin():
    db = get_db()
    dbase = FDATABASE(db)
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400
    
    uin = data.get('uin')
    password = data.get('password')
    if not all([uin, password]):
        return jsonify({"error": "Please provide UIN and password"}), 400

    user = dbase.get_user_by_uin(uin)
    if user and check_password_hash(user['password'], password):
        # Генерируем JWT-токен при успехе:
        payload = {
            "sub": uin,             # например, уникальный идентификатор
            "user_id": user['id'],
            "user_role": user['role'],
            "exp": datetime.utcnow() + timedelta(hours=24)  # срок действия 24 часа
        }
        # Берём секретный ключ из настроек приложения
        secret_key = current_app.config.get('SECRET_KEY', 'DBLFKJADSBCBALIasfGSGDSDHgdf6EF&ADL@E3213IL>SBBFL')  # <-- замените на реальный ключ

        token = jwt.encode(payload, secret_key, algorithm="HS256")
        if isinstance(token, bytes):
            token = token.decode('utf-8')  # на случай, если PyJWT вернёт bytes

        return jsonify({
            "success": True,
            "user_id": user['id'],
            "user_role": user['role'],
            "message": "Login by UIN successful",
            "token": token             # <-- добавляем поле token
        }), 200
    else:
        return jsonify({"error": "Invalid UIN or password"}), 401
 

# Регистрация Blueprint после определения всех его маршрутов
app.register_blueprint(api_bp, url_prefix='/api')

# Подключение к локальной БД
def connect_db():
    conn = psycopg2.connect(
        host="10.250.0.64",  # IP-адрес локального сервера
        port="5432",         # Порт по умолчанию
        user="postgres",     # Имя пользователя для PostgreSQL
        password="postgres", # Пароль пользователя
        database="attendance" # Имя вашей базы данных
    )
    return conn

# Получение соединения с БД
def get_db():
    if not hasattr(g, 'link_db'):
        g.link_db = connect_db()
    return g.link_db

dbase = None

@app.before_request
def before_request():
    print(f"Request path: {request.path}")
    print(f"Is API route: {request.path.startswith('/api/')}")
    global dbase
    db = get_db()
    dbase = FDATABASE(db)
    user_id = session.get('user_id')
    if user_id:
        g.user = dbase.get_user_by_id(user_id)
    else:
        g.user = None
        # Разрешаем доступ только к определенным маршрутам без авторизации
        if not request.path.startswith('/api/') and request.endpoint not in ('login', 'register', 'static'):
            print("Redirecting to login")
            return redirect(url_for('login'))

# Передаем объект соединения в FDATABASE
def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.get('user') is None:
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view
def admin_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        # Проверяем, авторизован ли пользователь
        if g.get('user') is None:
            return redirect(url_for('login'))
        # Проверяем, админ ли он
        if g.user['role'] != 'admin':
            flash("Доступ запрещён. Только для администраторов.", "error")
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view


# Маршрут регистрации
@app.route('/register', methods=['GET', 'POST'])
def register():
    db = get_db()
    dbase = FDATABASE(db)
    if request.method == 'POST':
        data = request.form
        name = data.get('name')
        email = data.get('email')
        phone_number = data.get('phone')
        password = data.get('password')

        if not all([name, email, phone_number, password]):
            flash('Пожалуйста, заполните все поля', 'error')
            return redirect(url_for('register'))

        if dbase.get_user_by_email(email):
            flash('Email уже зарегистрирован', 'error')
            return redirect(url_for('register'))

        # Разбиваем имя на first_name и last_name
        name_parts = name.strip().split()
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        patronymic = name_parts[2] if len(name_parts) > 2 else ''

        # Хэшируем пароль
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
        
        # Добавляем пользователя с ролью 'admin'
        success = dbase.add_user(first_name, last_name, patronymic, 'admin', phone_number, hashed_password, email)
        if success:
            flash('Регистрация успешна. Пожалуйста, войдите.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Ошибка при регистрации', 'error')
            return redirect(url_for('register'))
    else:
        return render_template('authentication-reg.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    db = get_db()
    dbase = FDATABASE(db)
    if request.method == 'POST':
        data = request.form
        email = data.get('email')
        password = data.get('password')

        if not all([email, password]):
            flash('Пожалуйста, заполните все поля', 'error')
            return redirect(url_for('login'))

        user = dbase.get_user_by_email(email)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_role'] = user['role']
            flash('Вход выполнен успешно', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверный email или пароль', 'error')
            return redirect(url_for('login'))
    else:
        return render_template('authentication-login.html')


# Маршрут выхода
@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'success')
    return redirect(url_for('login'))
@app.route("/download_pdf_selected", methods=["POST"])
def download_pdf_selected():
    data = request.get_json()
    selected_ids = data.get("ids", [])
    
    if not selected_ids:
        return jsonify({"error": "No IDs provided"}), 400
    
    db = get_db()
    dbase = FDATABASE(db)
    
    # Получаем информацию об аудиториях по выбранным ID
    classrooms = dbase.get_classrooms_by_ids(selected_ids)
    
    if not classrooms:
        return jsonify({"error": "No classrooms found for the provided IDs"}), 404
    
    # Генерация PDF с использованием существующих QR-кодов
    pdf_buffer = generate_pdf_with_qrcodes(classrooms)
    
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name="selected_classrooms.pdf",
        mimetype="application/pdf"
    )

@app.route("/download_pdf_all", methods=["GET"])
def download_pdf_all():
    db = get_db()
    dbase = FDATABASE(db)
    
    # Получаем информацию обо всех аудиториях
    classrooms = dbase.get_all_classrooms()
    
    if not classrooms:
        return jsonify({"error": "No classrooms found"}), 404
    
    # Генерация PDF с использованием существующих QR-кодов
    pdf_buffer = generate_pdf_with_qrcodes(classrooms)
    
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name="all_classrooms.pdf",
        mimetype="application/pdf"
    )


def generate_pdf_with_qrcodes(classrooms):
    # Регистрация шрифта с поддержкой кириллицы
    try:
        pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
    except Exception as e:
        print(f"Ошибка при регистрации шрифта: {e}")
        # Используем стандартный шрифт, если регистрация не удалась
        pass
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 20 * mm
    qr_size = 40 * mm
    y_position = height - margin
    
    for index, classroom in enumerate(classrooms, start=1):
        # Получаем путь к QR-коду из базы данных
        qr_code_relative_path = classroom.get('audience_qr')
        if qr_code_relative_path:
            # Преобразуем относительный путь в абсолютный путь
            absolute_qr_path = os.path.join(app.root_path, 'static', qr_code_relative_path)
            
            if os.path.exists(absolute_qr_path):
                try:
                    qr_image = ImageReader(absolute_qr_path)
                    # Добавляем QR-код в PDF
                    c.drawImage(qr_image, margin, y_position - qr_size, qr_size, qr_size)
                except Exception as e:
                    print(f"Ошибка при добавлении QR-кода для аудитории {classroom['audience_number']}: {e}")
                    c.setFont("DejaVuSans", 12)
                    c.drawString(margin, y_position - qr_size/2, "Ошибка загрузки QR-кода")
            else:
                print(f"QR-код не найден по пути: {absolute_qr_path}")
                c.setFont("DejaVuSans", 12)
                c.drawString(margin, y_position - qr_size/2, "QR-код отсутствует")
        else:
            print(f"Путь к QR-коду отсутствует для аудитории {classroom['audience_number']}")
            c.setFont("DejaVuSans", 12)
            c.drawString(margin, y_position - qr_size/2, "QR-код отсутствует")
        
        # Добавляем номер аудитории и другие детали
        classroom_number = classroom.get('audience_number', 'Неизвестно')
        classroom_type = classroom.get('audience_type', 'Неизвестно')
        
        # Устанавливаем шрифт и размер
        c.setFont("DejaVuSans", 12)
        text_x = margin + qr_size + 10
        text_y = y_position - 10
        c.drawString(text_x, text_y, f"#{index}: Аудитория {classroom_number} ({classroom_type})")
        
        y_position -= (qr_size + 20)  # Переходим на следующую строку
        
        # Добавляем новую страницу, если места не хватает
        if y_position < margin + qr_size:
            c.showPage()
            y_position = height - margin
    
    c.save()
    buffer.seek(0)
    return buffer

# ------------------------Аудитория
@app.route("/classrooms")
def classrooms():
    db = get_db()
    dbase = FDATABASE(db)
    classrooms=dbase.get_all_classrooms()
    return render_template("classroom.html",classrooms=classrooms)


@app.route("/classroom-add", methods=["POST", "GET"])
def addClassroom():
    db = get_db()
    dbase = FDATABASE(db)
    audience_types = dbase.get_audience_types()
    if request.method == "POST":
        classroom_number = request.form.get("classroom")
        classroom_type_id = request.form.get("role")
        
        if not classroom_number or not classroom_type_id:
            flash("Пожалуйста, заполните все поля", "error")
            return redirect(url_for("addClassroom"))
        # Используем метод add_classroom для добавления записи
        if dbase.add_classroom(classroom_number, classroom_type_id):
            flash("Аудитория успешно добавлена", "success")
            return redirect(url_for("classrooms"))
        else:
            flash("Ошибка при добавлении аудитории", "error")
            return redirect(url_for("addClassroom"))
    
    return render_template("classroom-add.html", audience_types=audience_types)


@app.route("/delete_classrooms", methods=["POST"])
def delete_classrooms():
    data = request.get_json()
    ids_to_delete = data.get("ids", [])

    if not ids_to_delete:
        return jsonify({"error": "No IDs provided"}), 400

    db = get_db()
    dbase = FDATABASE(db)

    success = dbase.delete_classrooms(ids_to_delete)

    if success:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": "Error deleting classrooms"}), 500

    
    return redirect(url_for("classrooms"))
@app.route("/classroom-update-qr/<int:audience_id>", methods=["POST"])
def update_classroom_qr(audience_id):
    db = get_db()
    dbase = FDATABASE(db)
    success = dbase.update_classroom_qr(audience_id)
    if success:
        return jsonify({"success": True, "message": "QR-код успешно обновлён"}), 200
    else:
        return jsonify({"error": "Ошибка при обновлении QR-кода"}), 500

# Новый маршрут для массового обновления QR-кодов всех аудиторий
@app.route("/classrooms/update-all-qr", methods=["POST"])
def update_all_qr():
    db = get_db()
    dbase = FDATABASE(db)
    success = dbase.update_all_qr_codes()
    if success:
        return jsonify({"success": True, "message": "Все QR-коды успешно обновлены"}), 200
    else:
        return jsonify({"error": "Ошибка при массовом обновлении QR-кодов"}), 500
# ------------------------Конец аудитории


# ------------------------Сотрудники
@app.route("/employees", methods=["GET"])
def employees():
    db = get_db()
    dbase = FDATABASE(db)
    employees = dbase.get_all_employees()
    subjects = dbase.get_subjects()
    return render_template("employees.html", employees=employees, subjects=subjects)

@app.route("/employees/add", methods=["GET", "POST"])
def add_employee():
    db = get_db()
    dbase = FDATABASE(db)
    
    if request.method == "POST":
        data = request.form
        role = data['role']
        subject_id = int(data['subject'])
        group_ids = request.form.getlist('groups')
        # uin = data['uin']
        
        # teacher_id = dbase.add_employee(
        #     first_name=data['firstName'],
        #     last_name=data['lastName'],
        #     patronymic=data['patronymic'],
        #     role=role,
        #     phone_number=data['phone'],
        #     password=generate_password_hash(data['password']),
        #     uin=uin
        # )
        import random
        uin = random.randint(100000000000,999999999999)
        teacher_id = dbase.add_employee(
            first_name=data['firstName'],
            last_name=data['lastName'],
            patronymic=data['patronymic'],
            role=role,
            phone_number=data['phone'],
            password=generate_password_hash(data['password'], method="pbkdf2:sha256"),
            uin=uin
        )
        if teacher_id:
            with open('login_passwords_employees.txt', 'a', encoding='utf-8') as f:
                f.write(f"{data['lastName']} {data['firstName']} {data['patronymic']} | {uin} | {data['password']}\n")
            success_subject_teacher = dbase.add_subject_teacher(subject_id, teacher_id, group_ids)
            if success_subject_teacher:
                flash("Сотрудник успешно добавлен", "success")
                return redirect(url_for('employees'))
        
        flash("Ошибка при добавлении сотрудника", "error")
        return redirect(url_for("add_employee"))
    
    roles = dbase.get_roles()
    subjects = dbase.get_subjects()
    groups = dbase.get_groups()
    return render_template("employees-add.html", roles=roles, subjects=subjects, groups=groups)


@app.route("/delete_employees", methods=["POST"])
def delete_employees():
    db = get_db()
    dbase = FDATABASE(db)
    data = request.get_json()
    employee_ids = data.get("ids", [])

    if not employee_ids:
        return jsonify({"error": "No IDs provided"}), 400

    success = dbase.delete_employees(employee_ids)
    if success:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": "Error deleting employees"}), 500

@app.route('/employees/details/<int:user_id>')
def employee_details(user_id):
    db = get_db()
    dbase = FDATABASE(db)
    employee = dbase.get_employee_details(user_id)
    if not employee:
        abort(404)
    
    attendance_records = dbase.get_employee_attendance(user_id)

    # employee уже содержит total_lessons_count и late_lessons_count,
    # если всё ок.

    return render_template(
        'employee-details.html',
        employee=employee,
        attendance_records=attendance_records
    )



# ------------------------Конец сотрудников
# ------------------------ Группы
@app.route('/groups/details/<int:group_id>')
def group_details(group_id):
    db = get_db()
    dbase = FDATABASE(db)
    group=dbase.get_group_details(group_id)
    students=dbase.get_group_students(group_id)
    return render_template('group-details.html',group=group,students=students)
@app.route("/delete_groups", methods=["POST"])
def delete_groups():
    db = get_db()
    dbase = FDATABASE(db)
    data = request.get_json()
    group_ids = data.get("ids", [])

    if not group_ids:
        return jsonify({"error": "Не указаны ID для удаления"}), 400

    # Проверка, что все IDs являются числами
    try:
        group_ids = [int(id) for id in group_ids]
    except ValueError:
        return jsonify({"error": "Некорректные ID"}), 400

    success = dbase.delete_groups(group_ids)
    if success:
        return jsonify({"success": True, "ids": group_ids}), 200
    else:
        return jsonify({"error": "Ошибка при удалении групп"}), 500

@app.route('/groups', methods=['GET'])
def groups():
    db = get_db()
    dbase = FDATABASE(db)
    groups = dbase.get_all_groups()
    import json
    from markupsafe import Markup
    groups_json = json.dumps(groups, default=str)
    specialties=dbase.get_specialties()
    return render_template('groups.html', groups_json=Markup(groups_json),specialties=specialties)

@app.route('/groups/add', methods=['GET', 'POST'])
def add_group():
    db = get_db()
    dbase = FDATABASE(db)
    if request.method == 'POST':
        data = request.form
        group_name = data['GroupNumber']
        course = data['course']
        language = data['language']
        specialty = data['specialty']
        curator_id = data['curator']

        # Получаем список выбранных студентов
        student_ids = request.form.getlist('student_ids')
        # Добавляем группу
        group_id = dbase.add_group(group_name, language, specialty, curator_id, student_ids,course)
        if group_id:
            # Назначаем студентов в группу
            success = dbase.assign_students_to_group(student_ids, group_name)
            if success:
                flash('Группа успешно добавлена', 'success')
                return redirect(url_for('groups'))
            else:
                flash('Ошибка при назначении студентов в группу', 'error')
        else:
            flash('Ошибка при добавлнии группы', 'error')

    # Получаем список студентов без группы
    students = dbase.get_students_with_group()
    # Получаем список кураторов
    curators = dbase.get_curators()
    courses = dbase.get_courses()
    specialties=dbase.get_specialties()
    languages=dbase.get_languages()
    return render_template('group-add.html', students=students, curators=curators, courses=courses,specs=specialties,languages=languages)

# Маршрут для создания группы с выбранными студентами
@app.route('/add_group_with_students', methods=['POST'])
def add_group_with_students():
    db = get_db()
    dbase = FDATABASE(db)
    group_name = request.form.get('group_name')
    language_id = request.form.get('language_id')
    specialty_id = request.form.get('specialty_id')
    curator_id = request.form.get('curator_id')
    student_ids = request.form.getlist('student_ids')

    if not all([group_name, language_id, specialty_id, curator_id, student_ids]):
        flash('Пожалуйста, заполните все поля и выберите студентов.', 'danger')
        return redirect(url_for('add_group_page'))

    success = dbase.add_group(group_name, language_id, specialty_id, curator_id, student_ids)
    if success:
        flash('Группа успешно создана.', 'success')
        return redirect(url_for('groups'))
    else:
        flash('Ошибка при создании группы.', 'danger')
        return redirect(url_for('add_group_page'))
# ------------------------ Конец групп
# ------------------------ Посещаемость
@app.route('/attendance', methods=['GET'])
def attendance():
    db = get_db()
    dbase = FDATABASE(db)
    
    groups = dbase.get_groups()
    # Получение данных для таблицы посещаемости
    report = dbase.get_all_attendance_report()
    import json
    from markupsafe import Markup
    attendance_report_json = json.dumps(report, default=str)
    
    print(groups)
    return render_template(
        'attendance.html',
        attendance_report=report,
        attendance_report_json=Markup(attendance_report_json),
        groups=groups
    )

# Новый маршрут для деталей посещаемости урока
@app.route('/attendance/<string:lessonid>/details', methods=['GET'])
def attendance_details(lessonid):
    db = get_db()
    dbase = FDATABASE(db)
    
    # Получение деталей посещаемости для конкретного урока
    attendance_details = dbase.get_attendance_details(lessonid)
    
    if not attendance_details:
        flash("Детали посещаемости не найдены для данного урока.", "error")
        return redirect(url_for('attendance'))
    # Получение общей информации об уроке
    # Для этого используем первую запись из attendance_details
    lesson_info = {
        'lesson_id': lessonid,
        'group_name': attendance_details[0]['group_name'],
        'subject_name': attendance_details[0]['subject_name'],
        'date': attendance_details[0]['starttime'].strftime('%Y-%m-%d'),
        'time': f"{attendance_details[0]['starttime'].strftime('%H:%M')} - {attendance_details[0]['endtime'].strftime('%H:%M')}",
        'teacher': attendance_details[0]['teacher']
    }
    import json
    from markupsafe import Markup
    attendance_details_json = json.dumps(attendance_details, default=str)
    # Подсчет статистики
    present_count = sum(1 for record in attendance_details if record['status_name'] in ['Присутствовал','Опоздал'])
    absent_count = sum(1 for record in attendance_details if record['status_name'] in ['Отсутствовал', 'Заболел'])
    
    stats = {
        'present': present_count,
        'absent': absent_count
    }
    return render_template(
        'attendance_students.html',
        lesson_info=lesson_info,
        attendance_details=attendance_details,
        stats=stats,
        lesson_id=lessonid,
        attendance_details_json=Markup(attendance_details_json)
    )

@app.route('/delete_lesson/<string:lessonid>')
def delete_lesson(lessonid):
    db = get_db()
    dbase = FDATABASE(db)
    dbase.delete_lesson(lessonid)
    return redirect(url_for('attendance'))
# ------------------------ Конец посещаемость
@app.route('/')
def index():
    db = get_db()
    dbase = FDATABASE(db)
    
    report = dbase.get_today_attendance_report()  # Метод, который возвращает "сегодняшнюю" посещаемость
    groups = dbase.get_groups()
    import json
    from markupsafe import Markup
    attendance_report_json = json.dumps(report, default=str)

    total_teachers = dbase.get_total_teachers()
    total_students = dbase.get_total_students()
    total_groups = dbase.get_total_groups()
    total_classrooms = dbase.get_total_classrooms()
    today = dbase.get_attendance_for_index()  # Возвращает топ опаздывающих по умолчанию

    return render_template(
        'index.html',
        total_teachers=total_teachers,
        total_students=total_students,
        total_groups=total_groups,
        total_classrooms=total_classrooms,
        attendance_report=report,
        attendance_report_json=Markup(attendance_report_json),
        groups=groups,
        today=today
    )

@app.route('/filtered_attendance', methods=['POST'])
def filtered_attendance():
    db = get_db()
    dbase = FDATABASE(db)
    filters = request.get_json()

    start_date = filters.get('start_date')
    end_date = filters.get('end_date')
    group_name = filters.get('group_name')
    course_name = filters.get('course_name')
    top_lateness = filters.get('top_lateness')  # True/False/None
    # Преобразуем входные данные top_lateness согласно логике:
    # top_lateness = True  -> top опаздывающих (больше всего опозданий)
    # top_lateness = False -> топ реже опаздывающих (меньше всего опозданий)
    # None -> без специализации, можно по умолчанию больше всего опозданий
    if top_lateness is True or top_lateness is False:
        pass
    else:
        # Если None, оставим сортировку по умолчанию — допустим, DESC
        top_lateness = None

    data = dbase.get_filtered_attendance_for_index(start_date, end_date, group_name, course_name, top_lateness)
    return jsonify(data)
@app.route('/rating', methods=['GET'])
def rating():
    db = get_db()
    dbase = FDATABASE(db)
    teachers = dbase.get_all_teachers()  # список преподавателей
    groups = dbase.get_groups()          # список групп
    courses = dbase.get_courses()        # список курсов

    initial_data = dbase.get_initial_rating()  # Получаем данные без фильтров
    # Передадим initial_data в шаблон через JSON
    import json
    from markupsafe import Markup
    initial_data_json = json.dumps(initial_data, default=str)

    return render_template('rating.html', teachers=teachers, groups=groups, courses=courses, initial_data_json=Markup(initial_data_json))


@app.route('/filtered_rating', methods=['POST'])
def filtered_rating():
    db = get_db()
    dbase = FDATABASE(db)
    filters = request.get_json()

    start_date = filters.get('start_date')
    end_date = filters.get('end_date')
    teacher = filters.get('teacher')
    group_name = filters.get('group_name')
    course_name = filters.get('course_name')

    data = dbase.get_filtered_rating(start_date, end_date, teacher, group_name, course_name)
    return jsonify(data)


# ------------------------ График
@app.route('/graph', methods=['GET'])
def graph():
    db = get_db()
    dbase = FDATABASE(db)
    graphs = dbase.get_all_graphs()
    return render_template('graph.html', graphs=graphs)


@app.route('/graph-add', methods=['GET', 'POST'])
def add_graph():
    db = get_db()
    dbase = FDATABASE(db)
    if request.method == 'POST':
        course = request.form.get('course')
        graph_name = request.form.get('graph_name')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        if not all([course, graph_name, start_date, end_date]):
            flash("Все поля обязательны для заполнения!", "error")
            return redirect(url_for('add_graph'))

        success = dbase.add_graph(course, graph_name, start_date, end_date)
        if success:
            flash("График успешно добавлен", "success")
            return redirect(url_for('graph'))
        else:
            flash("Ошибка при добавлении графика", "error")
            return redirect(url_for('add_graph'))
    
    return render_template('graph-add.html')
@app.route('/delete_graphs', methods=['POST'])
def delete_graphs():
    data = request.get_json()
    graph_ids = data.get("ids", [])

    if not graph_ids:
        return jsonify({"error": "Не указаны ID для удаления"}), 400

    db = get_db()
    dbase = FDATABASE(db)

    success = dbase.delete_graphs(graph_ids)
    if success:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": "Ошибка при удалении графиков"}), 500
# ------------------------ Cтуденты
@app.route('/students', methods=['GET'])
def students():
    db = get_db()
    dbase = FDATABASE(db)
    students = dbase.get_all_students()
    groups = dbase.get_groups()
    courses = dbase.get_courses()
    import json
    from markupsafe import Markup
    students_json = json.dumps(students, default=str)
    
    return render_template('students.html', students_json=Markup(students_json), groups=groups, courses=courses)

@app.route('/students/add', methods=['GET', 'POST'])
def add_student():
    db = get_db()
    dbase = FDATABASE(db)
    if request.method == 'POST':
        data = request.form
        import random
        uin = random.randint(100000000000,999999999999)
        success = dbase.add_student(
            first_name=data['firstName'],
            last_name=data['lastName'],
            patronymic=data['patronymic'],
            birthday = int(data['birthday'].replace('-', '')),
            phone_number=data['phone'],
            password=generate_password_hash(data['password'], method="pbkdf2:sha256"),
            # uin=data['uin']
            uin=uin
        )
        if success:
            flash('Студент успешно добавлен', 'success')
            with open('login_passwords_students.txt', 'a', encoding='utf-8') as f:
                f.write(f"{data['lastName']} {data['firstName']} {data['patronymic']} | {uin} | {data['password']}\n")
            return redirect(url_for('students'))
        else:
            flash('Ошибка при добавлении студента', 'error')
    return render_template('student-add.html')


@app.route('/students/details/<uin>', methods=['GET', 'POST'])
def student_details(uin):
    db = get_db()
    dbase = FDATABASE(db)
    
    if request.method == 'POST':
        data = request.form
        group_ids = data.getlist('group')  # Получаем список выбранных group_ids
        phone_number = data.get('phone_number')  # Получаем номер телефона
        
        success = dbase.update_student(
            uin=uin,
            group_ids=group_ids,
            phone_number=phone_number
        )
        
        if success:
            flash('Данные студента обновлены', 'success')
            return redirect(url_for('student_details', uin=uin))
        else:
            flash('Ошибка при обновлении данных студента', 'error')
    student = dbase.get_student_details(uin)
    if not student:
        abort(404)
    print(student)
    attendance_records = dbase.get_student_attendance(uin)
    all_groups = dbase.get_groups()  # Метод должен вернуть список всех групп
    
    return render_template('student-details.html', student=student, attendance_records=attendance_records, all_groups=all_groups)

@app.route('/delete_students', methods=['POST'])
def delete_students():
    data = request.json
    student_ids = data.get('ids', [])
    if not student_ids:
        return jsonify({'error': 'No student IDs provided'}), 400

    try:
        db = get_db()
        dbase = FDATABASE(db)
        success = dbase.delete_students(student_ids)
        if success:
            return jsonify({'message': 'Students deleted successfully'}), 200
        else:
            return jsonify({'error': 'Ошибка при удалении студентов'}), 500
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        print(f"Ошибка: {e}")
        return jsonify({'error': 'Произошла внутренняя ошибка'}), 500

@app.teardown_appcontext
def close_db(error):
    if hasattr(g,'link_db'):
        g.link_db.close()
if __name__== "__main__":
    app.run(debug=DEBUG, host="0.0.0.0", port=6688) 
