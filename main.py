from flask import Flask,render_template,url_for,request,session,redirect,g,abort,flash,jsonify,send_file
import psycopg2
from FDATABASE import FDATABASE
import psycopg2
import os
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import qrcode

DEBUG = True
SECRET_KEY = 'DBLFKJADSBCBALIasfGSGDSDHgdf6EF&ADL@E3213IL>SBBFL'
app = Flask(__name__)
upload_folder = os.path.join('static', 'uploads')
app.config['UPLOAD'] = upload_folder
app.config.from_object(__name__)

# подключение к локальной БД
def connect_db():
    conn = psycopg2.connect(
        host="10.250.0.64",  # IP-адрес локального сервера
        port="5432",         # Порт по умолчанию
        user="postgres",     # Имя пользователя для PostgreSQL
        password="postgres", # Пароль пользователя
        database="attendance" # Имя вашей базы данных
    )
    return conn

# получение соединения с БД
def get_db():
    if not hasattr(g, 'link_db'):
        g.link_db = connect_db()
    return g.link_db

dbase = None

@app.before_request
def before_request():
    global dbase
    db = get_db()
    dbase = FDATABASE(db)  # Передаем объект соединения в FDATABASE

@app.route("/download_pdf_selected", methods=["POST"])
def download_pdf_selected():
    data = request.get_json()
    selected_ids = data.get("ids", [])
    
    if not selected_ids:
        return jsonify({"error": "No IDs provided"}), 400
    
    db = get_db()
    dbase = FDATABASE(db)
    
    # Получаем информацию об аудиторіях по выбранным ID
    classrooms = dbase.get_classrooms_by_ids(selected_ids)
    
    if not classrooms:
        return jsonify({"error": "No classrooms found for the provided IDs"}), 404
    
    # Генерация PDF
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
    
    # Генерация PDF
    pdf_buffer = generate_pdf_with_qrcodes(classrooms)
    
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name="all_classrooms.pdf",
        mimetype="application/pdf"
    )

def generate_pdf_with_qrcodes(classrooms):
    # Регистрация шрифта с поддержкой кириллицы
    pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 20 * mm
    qr_size = 40 * mm
    y_position = height - margin
    
    for index, classroom in enumerate(classrooms, start=1):
        # Создание QR-кода
        qr_content = f"Номер аудитории: {classroom['audience_number']}, Тип: {classroom['audience_type']}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_content)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Сохранение QR-кода в байтовый поток
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        qr_image = ImageReader(img_buffer)
        
        # Добавление QR-кода и текста в PDF
        c.drawImage(qr_image, margin, y_position - qr_size, qr_size, qr_size)
        c.setFont("DejaVuSans", 12)  # Использование кириллического шрифта
        c.drawString(margin + qr_size + 10, y_position - 10, f"#{index}: Аудитория {classroom['audience_number']} ({classroom['audience_type']})")
        
        y_position -= (qr_size + 20)
        
        # Добавление новой страницы, если не хватает места
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
        uin = data['uin']
        
        teacher_id = dbase.add_employee(
            first_name=data['firstName'],
            last_name=data['lastName'],
            patronymic=data['patronymic'],
            role=role,
            phone_number=data['phone'],
            password=data['password'],
            uin=uin
        )
        
        if teacher_id:
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
    return render_template('groups.html', groups_json=Markup(groups_json))

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
            flash('Ошибка при добавлении группы', 'error')

    # Получаем список студентов без группы
    students = dbase.get_students_with_group()
    # Получаем список кураторов
    curators = dbase.get_curators()
    courses = dbase.get_courses()
    return render_template('group-add.html', students=students, curators=curators, courses=courses)

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
    
    # Получение данных для таблицы посещаемости
    attendance_report = dbase.get_attendance_report()
    report = dbase.get_all_attendance_report()
    # Получение данных для круговой диаграммы
    pie_data = dbase.get_weekly_attendance_summary()
    
    # Получение данных для столбчатой диаграммы
    bar_data_records = dbase.get_last_day_attendance_per_group()
    # Подготовка данных для круговой диаграммы
    pie_chart_data = {
        'present': pie_data['present'],
        'absent': pie_data['absent'],
    }
    # Подготовка данных для столбчатой диаграммы
    bar_chart_data = {
        'groups': [record['group_name'] for record in bar_data_records],
        'present': [record['present'] for record in bar_data_records],
        'absent': [record['absent'] for record in bar_data_records],
    }
    return render_template(
        'attendance.html',
        attendance_report=report,
        pie_data=pie_chart_data,
        bar_data=bar_chart_data
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
        lesson_id=lessonid
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
    
    # Получение статистики
    total_teachers = dbase.get_total_teachers()
    total_students = dbase.get_total_students()
    total_groups = dbase.get_total_groups()
    total_classrooms = dbase.get_total_classrooms()
    
    # Получение данных для графиков
    attendance_summary = dbase.get_weekly_attendance_summary()
    activity_data = dbase.get_activity_data()
    return render_template(
        'index.html',
        total_teachers=total_teachers,
        total_students=total_students,
        total_groups=total_groups,
        total_classrooms=total_classrooms,
        attendance_summary=attendance_summary,
        activity_data=activity_data
    )
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
        success = dbase.add_student(
            first_name=data['firstName'],
            last_name=data['lastName'],
            patronymic=data['patronymic'],
            birthday=data['birthday'],
            phone_number=data['phone'],
            password=data['password'],
            uin=data['uin']
        )
        if success:
            flash('Студент успешно добавлен', 'success')
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
    
    attendance_records = dbase.get_student_attendance(uin)
    all_groups = dbase.get_all_groups()  # Метод должен вернуть список всех групп
    
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
     
