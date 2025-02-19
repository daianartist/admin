from datetime import datetime
from psycopg2.extras import RealDictCursor
import os
import qrcode
class FDATABASE:
    def __init__(self, db):
        self.__db = db
        self.__cur = db.cursor(cursor_factory=RealDictCursor)
    # -------------------Аудитории
    def get_classrooms_by_ids(self, ids):
        if not ids:
            return []
        sql = """
            SELECT 
                audience_id,
                audience_number,
                audience_type_name AS AUDIENCE_TYPE,
                audiences.AUDIENCE_QR,
                TO_CHAR(audiences.AUDIENCE_QR_LAST_UPDATE, 'DD.MM.YY, HH24:MI') AS AUDIENCE_QR_LAST_UPDATE
            FROM 
                audiences
            JOIN 
                AUDIENCE_TYPES at ON AUDIENCES_TYPE = AUDIENCE_TYPE_ID
            WHERE 
                audience_id = ANY(%s);
        """
        try:
            self.__cur.execute(sql, (ids,))
            return self.__cur.fetchall()
        except Exception as e:
            print(f'Ошибка при получении аудиторий по ID: {e}')
            return []
    def get_all_classrooms(self):
        sql = """
            SELECT 
                a.AUDIENCE_ID,
                a.AUDIENCE_NUMBER,
                at.AUDIENCE_TYPE_NAME AS AUDIENCE_TYPE,
                a.AUDIENCE_QR,
                TO_CHAR(a.AUDIENCE_QR_LAST_UPDATE, 'DD.MM.YY, HH24:MI') AS AUDIENCE_QR_LAST_UPDATE
            FROM 
                AUDIENCES a
            JOIN 
                AUDIENCE_TYPES at ON a.AUDIENCES_TYPE = at.AUDIENCE_TYPE_ID
        """
        try:
            self.__cur.execute(sql)
            return self.__cur.fetchall() or []
        except Exception as e:
            print(f'Ошибка при чтении AUDIENCES: {e}')
            return []
    def get_audience_types(self):
        sql = "SELECT AUDIENCE_TYPE_ID, AUDIENCE_TYPE_NAME FROM AUDIENCE_TYPES"
        try:
            self.__cur.execute(sql)
            return self.__cur.fetchall() or []
        except Exception as e:
            print(f'Ошибка при чтении AUDIENCE_TYPES: {e}')
            return []
    def add_classroom(self, classroom_number, audience_type_id):
        try:
            # Вставляем новую аудиторию и получаем AUDIENCE_ID
            sql_insert = """
                INSERT INTO audiences (AUDIENCE_NUMBER, AUDIENCES_TYPE)
                VALUES (%s, %s)
                RETURNING AUDIENCE_ID
            """
            self.__cur.execute(sql_insert, (classroom_number, audience_type_id))
            audience_id = self.__cur.fetchone()['audience_id']
            print(f'Добавлена аудитория с ID: {audience_id}')
            
            # Генерация roomid, например, 'roomid:1.3.240'
            roomid = f'roomid:{classroom_number}'
            print(f'Сгенерирован roomid: {roomid}')
            
            # Создание QR-кода с содержимым roomid
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(roomid)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            print('QR-код сгенерирован')
            
            # Определение относительного пути для сохранения QR-кода
            qr_filename = f'roomid_{classroom_number}.png'
            qr_folder = os.path.join('static', 'uploads')  # относительный путь
            os.makedirs(qr_folder, exist_ok=True)  # Создаём папку, если её нет
            qr_path = os.path.join(qr_folder, qr_filename)
            img.save(qr_path)
            print(f'QR-код сохранён по пути: {qr_path}')
            
            # Обновление записи аудитории с относительным путем к QR-коду и временем обновления
            relative_qr_path = os.path.join('uploads', qr_filename)  # относительный путь от static
            sql_update = """
                UPDATE audiences
                SET AUDIENCE_QR = %s, AUDIENCE_QR_LAST_UPDATE = NOW()
                WHERE AUDIENCE_ID = %s
            """
            self.__cur.execute(sql_update, (relative_qr_path, audience_id))
            self.__db.commit()
            print('Запись AUDIENCES обновлена с QR-кодом и временем обновления')
            
            return True
        except Exception as e:
            self.__db.rollback()
            print(f'Ошибка при добавлении аудитории: {e}')
            return False
    def update_classroom_qr(self, audience_id):
        try:
            # Получаем номер аудитории по ID
            sql_get = "SELECT AUDIENCE_NUMBER FROM audiences WHERE AUDIENCE_ID = %s"
            self.__cur.execute(sql_get, (audience_id,))
            result = self.__cur.fetchone()
            if not result:
                print(f'Аудитория с ID {audience_id} не найдена.')
                return False
            classroom_number = result['AUDIENCE_NUMBER']
            
            # Генерация roomid
            roomid = f'roomid:{classroom_number}'
            print(f'Сгенерирован новый roomid: {roomid}')
            
            # Создание QR-кода
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(roomid)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            print('QR-код сгенерирован')
            
            # Определение относительного пути для сохранения QR-кода
            qr_filename = f'roomid_{classroom_number}.png'
            qr_folder = os.path.join('static', 'uploads')  # относительный путь
            os.makedirs(qr_folder, exist_ok=True)
            qr_path = os.path.join(qr_folder, qr_filename)
            img.save(qr_path)
            print(f'QR-код сохранён по пути: {qr_path}')
            
            # Обновление записи аудитории
            relative_qr_path = os.path.join('uploads', qr_filename)  # относительный путь от static
            sql_update = """
                UPDATE audiences
                SET AUDIENCE_QR = %s, AUDIENCE_QR_LAST_UPDATE = NOW()
                WHERE AUDIENCE_ID = %s
            """
            self.__cur.execute(sql_update, (relative_qr_path, audience_id))
            self.__db.commit()
            print('Запись AUDIENCES обновлена с новым QR-кодом и временем обновления')
            
            return True
        except Exception as e:
            self.__db.rollback()
            print(f'Ошибка при обновлении QR-кода аудитории: {e}')
            return False

    def update_all_qr_codes(self):
        try:
            # Получаем все аудитории
            sql_get_all = "SELECT AUDIENCE_ID, AUDIENCE_NUMBER FROM audiences"
            self.__cur.execute(sql_get_all)
            classrooms = self.__cur.fetchall()
            
            for class_room in classrooms:
                audience_id = class_room['audience_id']
                classroom_number = class_room['audience_number']
                
                # Генерация roomid
                roomid = f'roomid:{classroom_number}'
                print(f'Сгенерирован roomid: {roomid} для аудитории ID: {audience_id}')
                
                # Создание QR-кода
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(roomid)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                print(f'QR-код сгенерирован для аудитории ID: {audience_id}')
                
                # Определение относительного пути для сохранения QR-кода
                qr_filename = f'roomid_{classroom_number}.png'
                qr_folder = os.path.join('static', 'uploads')  # относительный путь
                os.makedirs(qr_folder, exist_ok=True)  # Создаём папку, если её нет
                qr_path = os.path.join(qr_folder, qr_filename)
                img.save(qr_path)
                print(f'QR-код сохранён по пути: {qr_path} для аудитории ID: {audience_id}')
                
                # Обновление записи аудитории с относительным путем к QR-коду и временем обновления
                relative_qr_path = os.path.join('uploads', qr_filename)  # относительный путь от static
                sql_update = """
                    UPDATE audiences
                    SET AUDIENCE_QR = %s, AUDIENCE_QR_LAST_UPDATE = NOW()
                    WHERE AUDIENCE_ID = %s
                """
                self.__cur.execute(sql_update, (relative_qr_path, audience_id))
                print(f'Запись AUDIENCES обновлена для аудитории ID: {audience_id}')
            
            self.__db.commit()
            print('Все QR-коды успешно обновлены.')
            return True
        except Exception as e:
            self.__db.rollback()
            print(f'Ошибка при массовом обновлении QR-кодов: {e}')
            return False

    def delete_classrooms(self, audience_ids):
        sql = "DELETE FROM AUDIENCES WHERE AUDIENCE_ID = ANY(%s::int[])"
        try:
            self.__cur.execute(sql, (audience_ids,))
            self.__db.commit()
            return True
        except Exception as e:
            self.__db.rollback()
            print(f'Ошибка при удалении аудиторий: {e}')
            return False
    # ----------------Конец аудиторий
    
    def get_user_by_uin(self, uin):
        sql = "SELECT * FROM users WHERE uin = %s"
        try:
            self.__cur.execute(sql, (uin,))
            return self.__cur.fetchone()
        except Exception as e:
            print(f'Ошибка при получении пользователя по UIN: {e}')
            return None

    #------------------ Сотрудники
    def add_user(self, first_name, last_name, patronymic, role, phone_number, password, email):
        try:
            import random
            # Генерируем UIN как инкрементное число
            new_uin = random.randint(1000,9999)
            
            sql = """
                INSERT INTO users (first_name, last_name, patronymic, role, phone_number, password, uin, email)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            self.__cur.execute(sql, (first_name, last_name, patronymic, role, phone_number, password, new_uin, email))
            user_id = self.__cur.fetchone()['id']
            self.__db.commit()
            return user_id
        except Exception as e:
            self.__db.rollback()
            print(f'Ошибка при добавлении пользователя: {e}')
            return None

    def get_user_by_email(self, email):
        sql = "SELECT * FROM users WHERE email = %s"
        try:
            self.__cur.execute(sql, (email,))
            user = self.__cur.fetchone()
            return user
        except Exception as e:
            print(f'Ошибка при получении пользователя по email: {e}')
            return None

    def get_user_by_id(self, user_id):
        sql = "SELECT * FROM users WHERE id = %s"
        try:
            self.__cur.execute(sql, (user_id,))
            user = self.__cur.fetchone()
            return user
        except Exception as e:
            print(f'Ошибка при получении пользователя по ID: {e}')
            return None

    def get_all_employees(self):
        sql = """
            SELECT 
                u.id AS user_id,
                u.first_name, 
                u.last_name, 
                u.patronymic, 
                u.role AS role_name, 
                COALESCE(s.subjects, 'Нет данных') AS subject_name,
                CASE 
                    WHEN cg.curator_count > 0 THEN 'Да'
                    ELSE 'Нет'
                END AS curator,
                COALESCE(cg.own_groups, 'Нет') AS own_groups,
                COALESCE(sa.lateness, 0) AS lateness,
                COALESCE(sa.missed_classes, 0) AS missed_classes
            FROM 
                users u
            LEFT JOIN (
                -- Агрегация предметов, которые преподает преподаватель
                SELECT st.teacher_id, string_agg(DISTINCT s.subject_name, ' / ') AS subjects
                FROM subjects_teachers st
                JOIN subjects s ON st.subject_id = s.subject_id
                GROUP BY st.teacher_id
            ) s ON u.id = s.teacher_id
            LEFT JOIN (
                -- Агрегация групп, за которые преподаватель является куратором
                SELECT 
                    g.curator_id AS teacher_id, 
                    string_agg(DISTINCT g.group_name, ' / ') AS own_groups,
                    COUNT(*) AS curator_count
                FROM groups g
                WHERE g.curator_id IS NOT NULL
                GROUP BY g.curator_id
            ) cg ON u.id = cg.teacher_id
            LEFT JOIN (
                -- Подсчет опозданий и пропущенных занятий для преподавателей на основе uin
                SELECT 
                    u.uin,
                    COUNT(*) FILTER (WHERE sa.status = 'Опоздал') AS lateness,
                    COUNT(*) FILTER (WHERE sa.status IN ('Отсутствовал', 'Заболел')) AS missed_classes
                FROM student_attendance sa
                JOIN users u ON sa.uin = u.uin
                WHERE u.role = 'student'
                GROUP BY u.uin
            ) sa ON u.uin = sa.uin
            WHERE 
                u.role != 'student'
            ORDER BY 
                u.last_name, u.first_name;
        """
        try:
            self.__cur.execute(sql)
            return self.__cur.fetchall() or []
        except Exception as e:
            print(f'Ошибка при чтении сотрудников: {e}')
            return []

    
    def add_employee(self, first_name, last_name, patronymic, role, phone_number, password, uin):
        sql = """
            INSERT INTO users (first_name, last_name, patronymic, role, phone_number, password, uin)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
        """
        try:
            self.__cur.execute(sql, (first_name, last_name, patronymic, role, phone_number, password, uin))
            user_id = self.__cur.fetchone()['id']
            self.__db.commit()
            return user_id  # Возвращаем ID нового сотрудника
        except Exception as e:
            self.__db.rollback()
            print(f'Ошибка при добавлении сотрудника: {e}')
            return None

    def delete_employees(self, employee_ids):
        sql = "DELETE FROM users WHERE id = ANY(%s::int[])"
        try:
            self.__cur.execute(sql, (employee_ids,))
            self.__db.commit()
            return True
        except Exception as e:
            self.__db.rollback()
            print(f'Ошибка при удалении сотрудников: {e}')
            return False

    def get_roles(self):
        sql = "SELECT DISTINCT role AS role_name FROM users"
        try:
            self.__cur.execute(sql)
            roles = self.__cur.fetchall() or []
            # Добавляем роли "teacher" и "student" если их нет
            role_names = [role['role_name'] for role in roles]
            if 'teacher' not in role_names:
                roles.append({'role_name': 'teacher'})
            if 'student' not in role_names:
                roles.append({'role_name': 'student'})
            return roles
        except Exception as e:
            print(f'Ошибка при получении ролей: {e}')
            return []

    def get_subjects(self):
        sql = "SELECT subject_id, subject_name FROM subjects"
        try:
            self.__cur.execute(sql)
            return self.__cur.fetchall() or []
        except Exception as e:
            print(f'Ошибка при чтении предметов: {e}')
            return []

    def get_groups(self):
        sql = "SELECT group_id, group_name FROM groups"
        try:
            self.__cur.execute(sql)
            return self.__cur.fetchall() or []
        except Exception as e:
            print(f'Ошибка при чтении групп: {e}')
            return []

    def add_subject_teacher(self, subjects_ids, teacher_id, group_ids=None):
        try:
            if not isinstance(subjects_ids, list):
                subjects_ids = [subjects_ids]  # Преобразуем в список, если передан один предмет

            sql_with_group = "INSERT INTO subjects_teachers (subject_id, teacher_id, group_id) VALUES (%s, %s, %s)"
            sql_without_group = "INSERT INTO subjects_teachers (subject_id, teacher_id) VALUES (%s, %s)"

            for subject_id in subjects_ids:
                if group_ids:
                    for group_id in group_ids:
                        self.__cur.execute(sql_with_group, (subject_id, teacher_id, group_id))
                else:
                    self.__cur.execute(sql_without_group, (subject_id, teacher_id))

            self.__db.commit()
            return True
        except Exception as e:
            self.__db.rollback()
            print(f'Ошибка при добавлении записи в subjects_teachers: {e}')
            return False


    #----------------Конец сотрудников 
    def showGroups(self):
        sql="""
            SELECT GROUP_ID AS GROUP_ID, GROUP_NAME AS GROUP_NAME,COURSE AS COURSE,SPECIALTY_NAME AS SPECIALTY_NAME, LAST_NAME AS CURATOR_LAST_NAME,FIRST_NAME AS CURATOR_FIRST_NAME, LANGUAGE_NAME AS LANGUAGE_NAME
            FROM GROUPS 
            INNER JOIN USERS ON CURATOR_ID=USER_ID
            INNER JOIN SPECIALTIES ON SPECIALTIES.specialty_id=GROUPS.speciality_id
            INNER JOIN LANGUAGES ON LANGUAGES.LANGUAGE_ID=GROUPS.LANGUAGE_ID 
        """
        try:
            self.__cur.execute(sql)
            return self.__cur.fetchall() or []
        except Exception as e:
            print(f'Ошибка при чтении групп: {e}')
            return []
    def get_specialty_id_by_name(self,specialty_name):
        sql="SELECT specialty_id FROM SPECIALTIES WHERE specialty_name=%s"
        try:
            self.__cur.execute(sql,(specialty_name,))
            return self.__cur.fetchone() or {}
        except Exception as e:
            print(f'Ошибка при чтении групп: {e}')
            return []
    def get_specialties(self):
        sql="SELECT * FROM SPECIALTIES"
        try:
            self.__cur.execute(sql)
            return self.__cur.fetchall() or []
        except Exception as e:
            print(f'Ошибка при чтении групп: {e}')
            return []
    def get_group_details(self,group_id):
        sql="""
            SELECT GROUP_ID AS GROUP_ID, GROUP_NAME AS GROUP_NAME,COURSE AS COURSE,SPECIALITY_ID AS SPECIALTY_NAME, LAST_NAME AS CURATOR_LAST_NAME,FIRST_NAME AS CURATOR_FIRST_NAME, LANGUAGE_ID AS LANGUAGE_NAME
FROM GROUPS 
INNER JOIN USERS ON CURATOR_ID=USERS.ID WHERE GROUP_ID=%s
        """
        try:
            self.__cur.execute(sql,(group_id,))
            return self.__cur.fetchone() or {}
        except Exception as e:
            print(f'Ошибка при чтении группы: {e}')
            return []
    def get_group_students(self,group_id):
        sql="""
            SELECT DISTINCT STUDENT_ID AS STUDENT_ID, FIRST_NAME AS STUDENT_FIRST_NAME,LAST_NAME AS STUDENT_LAST_NAME 
            FROM STUDENTS_GROUPS 
            INNER JOIN USERS ON STUDENT_ID=ID
            WHERE GROUP_ID=%s
        """
        try:
            self.__cur.execute(sql,(group_id,))
            return self.__cur.fetchall() or []
        except Exception as e:
            print(f'Ошибка при чтении группы: {e}')
            return []
    def delete_groups(self, group_ids):
        sql = "DELETE FROM groups WHERE group_id = ANY(%s::int[])"
        try:
            self.__cur.execute(sql, (group_ids,))
            self.__db.commit()
            return True
        except Exception as e:
            self.__db.rollback()
            print(f'Ошибка при удалении групп: {e}')
            return False

    def get_languages(self):
        sql = "SELECT language_id, language_name FROM languages"
        try:
            self.__cur.execute(sql)
            return self.__cur.fetchall() or []
        except Exception as e:
            print(f'Ошибка при получении языков: {e}')
            return []
        
    def get_all_groups(self):
        sql = """
            SELECT 
                g.group_id,
                g.group_name,
                g.course,
                specialties.specialty_name,
                LANGUAGES.language_name,
                u.first_name AS curator_first_name,
                u.last_name AS curator_last_name
            FROM groups g
            LEFT JOIN users u ON g.curator_id = u.id
			INNER JOIN specialties on g.speciality_id=specialties.specialty_id
			INNER JOIN LANGUAGES on g.language_id=languages.language_id
        """
        try:
            self.__cur.execute(sql)
            return self.__cur.fetchall() or []
        except Exception as e:
            print(f'Ошибка при получении списка групп: {e}')
            return []

    
    def assign_students_to_group(self, student_ids, group_id):
        sql= "SELECT GROUP_ID FROM GROUPS WHERE GROUP_NAME=%s"
        self.__cur.execute(sql,(group_id,))
        group=self.__cur.fetchone()
        sql = """
            INSERT INTO students_groups (student_id, group_id)
            VALUES (%s, %s)
        """
        try:
            for student_id in student_ids:
                self.__cur.execute(sql, (student_id, group['group_id']))
            self.__db.commit()
            return True
        except Exception as e:
            self.__db.rollback()
            print(f'Ошибка при назначении студентов в группу: {e}')
            return False


    def get_students_with_group(self):
        sql = """
            SELECT 
                u.id,
                u.first_name,
                u.last_name,
                u.patronymic,
                u.birthday,
                u.uin
            FROM users u
            WHERE u.role = 'student'
        """
        try:
            self.__cur.execute(sql)
            return self.__cur.fetchall() or []
        except Exception as e:
            print(f'Ошибка при получении студентов без группы: {e}')
            return []

    # Метод для получения ID роли по названию
    def get_role_id_by_name(self, role_name):
        sql = "SELECT role_id FROM roles WHERE role_name = %s"
        try:
            self.__cur.execute(sql, (role_name,))
            result = self.__cur.fetchone()
            return result['role_id'] if result else None
        except Exception as e:
            print(f'Ошибка при получении ID роли: {e}')
            return None

    # Метод для получения всех студентов
    def get_all_students(self):
        sql = """
            SELECT
                u.id AS student_id,
                u.first_name,
                u.last_name,
                u.patronymic,
                u.uin,
                COALESCE(MIN(g.course::text), 'Нет данных') AS course,
                COALESCE(string_agg(DISTINCT g.group_name, ' / '), 'Нет данных') AS group_names,
                COALESCE(
                    (SELECT COUNT(*) FROM student_attendance sa WHERE sa.status = 'yellow' AND sa.uin = u.uin),
                    0
                ) AS lateness,
                COALESCE(
                    (SELECT COUNT(*) FROM student_attendance sa WHERE sa.status IN ('Отсутствовал', 'Заболел', 'red') AND sa.uin = u.uin),
                    0
                ) AS missed_classes
            FROM users u
            LEFT JOIN students_groups sg ON u.id = sg.student_id
            LEFT JOIN groups g ON sg.group_id = g.group_id
            WHERE u.role = 'student'
            GROUP BY u.id
            ORDER BY u.last_name, u.first_name
        """
        try:
            self.__cur.execute(sql)
            return self.__cur.fetchall() or []
        except Exception as e:
            print(f'Ошибка при получении списка студентов: {e}')
            return []



    def get_courses(self):
        # sql = "SELECT DISTINCT course FROM groups ORDER BY course"
        # try:
        #     self.__cur.execute(sql)
        #     courses = [row['course'] for row in self.__cur.fetchall()]
        #     return courses
        # except Exception as e:
        #     print(f'Ошибка при получении курсов: {e}')
        #     return []
        return ["1", "2", "3"]
    # Метод для получения списка кураторов
    def get_curators(self):
        sql = """
            SELECT u.id, u.first_name, u.last_name
            FROM users u
            WHERE u.role = 'teacher'
        """
        try:
            self.__cur.execute(sql)
            return self.__cur.fetchall() or []
        except Exception as e:
            print(f'Ошибка при получении списка кураторов: {e}')
            return []

    # Метод для получения студентов без группы

    # Обновленный метод для добавления группы с привязкой студентов
    def add_group(self, group_name, language_id, specialty_id, curator_id, student_ids,course):
        try:
            # Вставка новой группы в таблицу groups
            sql_insert_group = """
                INSERT INTO groups (group_name, speciality_id, curator_id, language_id,course)
                VALUES (%s, %s, %s, %s,%s)
                RETURNING group_id
            """
            self.__cur.execute(sql_insert_group, (group_name, specialty_id, curator_id, language_id,course))
            group_id = self.__cur.fetchone()['group_id']

            # Вставка студентов в таблицу students_groups
            sql_insert_student_group = """
                INSERT INTO students_groups (student_id, group_id)
                VALUES (%s, %s)
            """
            for student_id in student_ids:
                self.__cur.execute(sql_insert_student_group, (student_id, group_id))

            self.__db.commit()
            return True
        except Exception as e:
            self.__db.rollback()
            print(f'Ошибка при добавлении группы: {e}')
            return False
    # -------------------- Посещаемость
    def get_attendance_for_index(self):
        sql = """
            WITH lateness_counts AS (
                SELECT sa.uin, COUNT(*) AS lateness
                FROM student_attendance sa
                WHERE sa.status = 'yellow'
                GROUP BY sa.uin
            )
            SELECT
                u.uin,
                u.last_name,
                u.first_name,
                u.patronymic,
                COALESCE(string_agg(DISTINCT g.group_name, ' / '), 'Нет данных') AS group_names,
                COALESCE(MIN(g.course::text), 'Нет данных') AS course,
                COALESCE(lc.lateness, 0) AS lateness
            FROM users u
            LEFT JOIN students_groups sg ON u.id = sg.student_id
            LEFT JOIN groups g ON sg.group_id = g.group_id
            LEFT JOIN lateness_counts lc ON u.uin = lc.uin
            WHERE u.role = 'student'
            GROUP BY u.id, lc.lateness
            ORDER BY lateness DESC;
        """
        
        try:
            self.__cur.execute(sql)
            rows = self.__cur.fetchall() or []
            return rows
        except Exception as e:
            print(f'Ошибка при получении списка get_attendance_for_index: {e}')
            return []
    def get_filtered_attendance_for_index(self, start_date, end_date, group_name, course_name, top_lateness):
        conditions = []
        params = {}

        # Фильтр по дате
        date_filter = ""
        if start_date and end_date:
            date_filter = "AND l.starttime::date BETWEEN %(start_date)s AND %(end_date)s"
            params['start_date'] = start_date
            params['end_date'] = end_date
        elif start_date:
            date_filter = "AND l.starttime::date >= %(start_date)s"
            params['start_date'] = start_date
        elif end_date:
            date_filter = "AND l.starttime::date <= %(end_date)s"
            params['end_date'] = end_date

        # Фильтр по группе
        if group_name:
            conditions.append("""
                EXISTS (
                    SELECT 1 FROM students_groups sgg
                    JOIN groups gg ON sgg.group_id = gg.group_id
                    WHERE sgg.student_id = u.id
                    AND gg.group_name = %(group_name)s
                )
            """)
            params['group_name'] = group_name

        # Фильтр по курсу
        if course_name:
            conditions.append("""
                EXISTS (
                    SELECT 1 FROM students_groups sgg2
                    JOIN groups gg2 ON sgg2.group_id = gg2.group_id
                    WHERE sgg2.student_id = u.id
                    AND gg2.course = %(course_name)s
                )
            """)
            params['course_name'] = course_name

        # CTE для подсчёта опозданий с учётом фильтрации по дате
        cte = """
            WITH lateness_counts AS (
                SELECT sa.uin, COUNT(*) AS lateness
                FROM student_attendance sa
                JOIN lessons l ON sa.lessonid = l.lessonid
                WHERE sa.status = 'yellow'
                {date_filter}
                GROUP BY sa.uin
            )
        """.format(date_filter=date_filter)

        # Базовый SQL-запрос с использованием LEFT JOIN
        sql = f"""
            {cte}
            SELECT
                u.uin,
                u.last_name,
                u.first_name,
                u.patronymic,
                COALESCE(string_agg(DISTINCT g.group_name, ' / '), 'Нет данных') AS group_names,
                COALESCE(MIN(g.course::text), 'Нет данных') AS course,
                COALESCE(lc.lateness, 0) AS lateness
            FROM users u
            LEFT JOIN students_groups sg ON u.id = sg.student_id
            LEFT JOIN groups g ON sg.group_id = g.group_id
            LEFT JOIN lateness_counts lc ON u.uin = lc.uin
            WHERE u.role = 'student'
        """

        # Добавление дополнительных условий фильтрации
        if conditions:
            sql += " AND " + " AND ".join(conditions)

        # Группировка по студенту и опозданиям
        sql += """
            GROUP BY u.id, lc.lateness
        """

        # Сортировка по опозданиям
        if top_lateness is True:
            # Больше всего опозданий
            sql += " ORDER BY lateness DESC"
        elif top_lateness is False:
            # Меньше всего опозданий
            sql += " ORDER BY lateness ASC"
        else:
            # По умолчанию: больше всего опозданий
            sql += " ORDER BY lateness DESC"

        try:
            self.__cur.execute(sql, params)
            rows = self.__cur.fetchall() or []
            result = []
            for row in rows:
                result.append({
                    'uin': row['uin'],
                    'last_name': row['last_name'],
                    'first_name': row['first_name'],
                    'patronymic': row['patronymic'],
                    'group_names': row['group_names'],
                    'course': row['course'],
                    'lateness': row['lateness']
                })
            return result
        except Exception as e:
            print(f'Ошибка при получении фильтрованного рейтинга: {e}')
            return []






    def get_today_attendance_report(self):
        sql = """
            SELECT 
                l.lessonid,
                l.starttime::date AS date,
                l."group" AS group_name,
                l.teacher AS teacher,
                TO_CHAR(l.starttime, 'HH24:MI') || '-' || TO_CHAR(l.endtime, 'HH24:MI') AS time,
                COUNT(CASE WHEN sa.status IN ('green', 'yellow') THEN sa.uin END) AS present,
                COUNT(CASE WHEN sa.status IN ('red') THEN sa.uin END) AS absent
            FROM lessons l
            LEFT JOIN student_attendance sa ON l.lessonid = sa.lessonid
            WHERE 
                l.starttime::date = CURRENT_DATE
            GROUP BY l.lessonid, date, group_name, teacher, time
            ORDER BY date DESC, group_name, l.starttime DESC;
        """
        try:
            self.__cur.execute(sql)
            results = self.__cur.fetchall() or []
            return results
        except Exception as e:
            print(f'Ошибка при чтении посещаемости: {e}')
            self.__db.rollback()
            return []
    def get_all_attendance_report(self):
        # sql = """
        #     SELECT 
        #         l.lessonid,
        #         l.starttime::date AS date,
        #         l."group" AS group_name,
        #         l.teacher AS teacher,
        #         TO_CHAR(l.starttime, 'HH24:MI') || '-' || TO_CHAR(l.endtime, 'HH24:MI') AS time,
        #         COUNT(CASE WHEN sa.status IN ('green', 'yellow') THEN sa.uin END) AS present,
        #         COUNT(CASE WHEN sa.status IN ('red') THEN sa.uin END) AS absent
        #     FROM lessons l
        #     LEFT JOIN student_attendance sa ON l.lessonid = sa.lessonid
        #     WHERE 
        #         l.starttime >= CURRENT_DATE - INTERVAL '7 days'
        #     GROUP BY l.lessonid, date, group_name, teacher, time
        #     ORDER BY date DESC, group_name, l.starttime DESC;
        # """
        sql = """
            SELECT 
                l.lessonid,
                l.starttime::date AS date,
                l."group" AS group_name,
                l.teacher AS teacher,
                TO_CHAR(l.starttime, 'HH24:MI') || '-' || TO_CHAR(l.endtime, 'HH24:MI') AS time,
                COUNT(CASE WHEN sa.status IN ('green', 'yellow') THEN sa.uin END) AS present,
                COUNT(CASE WHEN sa.status IN ('red') THEN sa.uin END) AS absent
            FROM lessons l
            LEFT JOIN student_attendance sa ON l.lessonid = sa.lessonid
            GROUP BY l.lessonid, date, group_name, teacher, time
            ORDER BY date DESC, group_name, l.starttime DESC;
        """
        try:
            self.__cur.execute(sql)
            results = self.__cur.fetchall() or []
            return results
        except Exception as e:
            print(f'Ошибка при чтении посещаемости: {e}')
            self.__db.rollback()
            return []

    def get_attendance_report(self):
        sql = """
            SELECT 
                l.lessonid,
                l.starttime::date AS date,
                l."group" AS group_name,
                l.teacher AS teacher,
                TO_CHAR(l.starttime, 'HH24:MI') || '-' || TO_CHAR(l.endtime, 'HH24:MI') AS time,
                COUNT(CASE WHEN sa.status IN ('green', 'yellow') THEN sa.uin END) AS present,
                COUNT(CASE WHEN sa.status IN ('red') THEN sa.uin END) AS absent
            FROM lessons l
            LEFT JOIN student_attendance sa ON l.lessonid = sa.lessonid
            WHERE 
                l.starttime >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY l.lessonid, date, group_name, teacher, time
            ORDER BY date DESC, group_name, l.starttime DESC;
        """
        try:
            self.__cur.execute(sql)
            results = self.__cur.fetchall() or []
            return results
        except Exception as e:
            print(f'Ошибка при получении отчета посещаемости: {e}')
            self.__db.rollback()
            return []

    def get_attendance_details(self, lessonid):
        sql = """
            SELECT 
                u.id AS student_id,
                u.first_name AS student_first_name,
                u.last_name AS student_last_name,
                u.patronymic,
                l.description AS subject_name,
                u."group" AS group_name,
                l.starttime,
                l.endtime,
                TO_CHAR(sa.scantime, 'HH24:MI') AS scantime,
                l.teacher AS teacher,
                sa.status AS status_name
            FROM 
                student_attendance sa
            JOIN 
                users u ON sa.uin = u.uin
            JOIN 
                lessons l ON sa.lessonid = l.lessonid
            WHERE 
                sa.lessonid = %s
                AND u.role = 'student'
        """
        try:
            self.__cur.execute(sql, (lessonid,))
            return self.__cur.fetchall() or []
        except Exception as e:
            print(f'Ошибка при получении деталей посещаемости урока {lessonid}: {e}')
            self.__db.rollback()
            return []

    def delete_lesson(self, lessonid):
        sql = "DELETE FROM lessons WHERE lessonid = %s"
        try:
            self.__cur.execute(sql, (lessonid,))
            self.__db.commit()
            return True
        except Exception as e:
            self.__db.rollback()
            print(f'Ошибка при удалении урока: {e}')
            return False

    def get_weekly_attendance_summary(self):
        sql = """
            SELECT
                COUNT(CASE WHEN sa.status IN ('Присутствовал', 'Опоздал') THEN sa.uin END) AS present,
                COUNT(CASE WHEN sa.status IN ('Отсутствовал', 'Заболел') THEN sa.uin END) AS absent
            FROM student_attendance sa
            JOIN lessons l ON sa.lessonid = l.lessonid
            WHERE 
                l.starttime >= CURRENT_DATE - INTERVAL '7 days'
        """
        try:
            self.__cur.execute(sql)
            result = self.__cur.fetchone()
            present = result['present'] or 0
            absent = result['absent'] or 0
            return {'present': present, 'absent': absent}
        except Exception as e:
            print(f'Ошибка при получении еженедельной сводки посещаемости: {e}')
            return {'present': 0, 'absent': 0}

    def get_last_day_attendance_per_group(self):
        sql = """
            WITH last_day AS (
                SELECT MAX(starttime::date) AS last_date FROM lessons
            )
            SELECT
                l."group" AS group_name,
                COUNT(CASE WHEN sa.status IN ('Присутствовал', 'Опоздал') THEN sa.uin END) AS present,
                COUNT(CASE WHEN sa.status IN ('Отсутствовал', 'Заболел') THEN sa.uin END) AS absent
            FROM lessons l
            JOIN last_day ld ON l.starttime::date = ld.last_date
            LEFT JOIN student_attendance sa ON l.lessonid = sa.lessonid
            GROUP BY l."group"
            ORDER BY l."group"
        """
        try:
            self.__cur.execute(sql)
            return self.__cur.fetchall() or []
        except Exception as e:
            print(f'Ошибка при получении посещаемости за последний день по группам: {e}')
            return []

    def get_activity_data(self):
        sql = """
            SELECT 
                TO_CHAR(l.starttime, 'FMDay') AS day,
                COUNT(CASE WHEN sa.status IN ('Присутствовал', 'Опоздал') THEN sa.uin END) AS present_count
            FROM lessons l
            LEFT JOIN student_attendance sa ON l.lessonid = sa.lessonid
            WHERE 
                l.starttime >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY day
            ORDER BY 
                CASE 
                    WHEN TO_CHAR(l.starttime, 'FMDay') ILIKE 'Monday' THEN 1
                    WHEN TO_CHAR(l.starttime, 'FMDay') ILIKE 'Tuesday' THEN 2
                    WHEN TO_CHAR(l.starttime, 'FMDay') ILIKE 'Wednesday' THEN 3
                    WHEN TO_CHAR(l.starttime, 'FMDay') ILIKE 'Thursday' THEN 4
                    WHEN TO_CHAR(l.starttime, 'FMDay') ILIKE 'Friday' THEN 5
                    WHEN TO_CHAR(l.starttime, 'FMDay') ILIKE 'Saturday' THEN 6
                    WHEN TO_CHAR(l.starttime, 'FMDay') ILIKE 'Sunday' THEN 7
                    ELSE 8
                END;
        """
        try:
            self.__cur.execute(sql)
            results = self.__cur.fetchall() or []
            labels = [result['day'] for result in results]
            values = [result['present_count'] for result in results]
            return {'labels': labels, 'values': values}
        except Exception as e:
            print(f'Ошибка при получении данных активности студентов: {e}')
            return {'labels': [], 'values': []}
    def get_initial_rating(self):
        sql = """
            SELECT
                u.uin,
                u.last_name,
                u.first_name,
                u.patronymic,
                COALESCE(string_agg(DISTINCT g.group_name, ' / '), 'Нет данных') AS group_names,
                COALESCE(MIN(g.course::text), 'Нет данных') AS course,
                COUNT(DISTINCT CASE WHEN sa.status='green' THEN sa.lessonid END) AS green_count,
                COUNT(DISTINCT CASE WHEN sa.status='yellow' THEN sa.lessonid END) AS yellow_count,
                COUNT(DISTINCT CASE WHEN sa.status='red' THEN sa.lessonid END) AS red_count,
                COUNT(DISTINCT sa.lessonid) AS total,
                CASE 
                    WHEN COUNT(DISTINCT sa.lessonid) > 0 THEN 
                        ROUND((COUNT(DISTINCT CASE WHEN sa.status='green' THEN sa.lessonid END)::decimal / COUNT(DISTINCT sa.lessonid)) * 100, 2)
                    ELSE 0 
                END AS quality_percent,
                CASE 
                    WHEN COUNT(DISTINCT sa.lessonid) > 0 THEN 
                        ROUND(((COUNT(DISTINCT CASE WHEN sa.status IN ('green','yellow') THEN sa.lessonid END)::decimal / COUNT(DISTINCT sa.lessonid)) * 100), 2)
                    ELSE 0 
                END AS attendance_percent
            FROM users u
            LEFT JOIN students_groups sg ON u.id = sg.student_id
            LEFT JOIN groups g ON sg.group_id = g.group_id
            LEFT JOIN student_attendance sa ON u.uin = sa.uin
            WHERE u.role = 'student'
            GROUP BY u.id
            ORDER BY u.last_name, u.first_name
        """
        
        try:
            self.__cur.execute(sql)
            rows = self.__cur.fetchall() or []
            return rows
        except Exception as e:
            print(f'Ошибка при получении начального рейтинга: {e}')
            return []





    def get_filtered_rating(self, start_date, end_date, teacher, group_name, course_name):
        params = {}
        conditions = []

        # Фильтр по дате
        date_condition = ""
        if start_date and end_date:
            date_condition = "AND l.starttime::date BETWEEN %(start_date)s AND %(end_date)s"
            params['start_date'] = start_date
            params['end_date'] = end_date
        elif start_date:
            date_condition = "AND l.starttime::date >= %(start_date)s"
            params['start_date'] = start_date
        elif end_date:
            date_condition = "AND l.starttime::date <= %(end_date)s"
            params['end_date'] = end_date

        # Фильтр по преподавателю
        teacher_condition = ""
        if teacher:
            teacher_condition = "AND l.teacher = %(teacher)s"
            params['teacher'] = teacher

        # Базовый SQL-запрос с использованием LEFT JOIN
        sql = f"""
            SELECT
                u.uin,
                u.last_name,
                u.first_name,
                u.patronymic,
                COALESCE(string_agg(DISTINCT g.group_name, ' / '), 'Нет данных') AS group_names,
                COALESCE(MIN(g.course::text), 'Нет данных') AS course,
                COUNT(DISTINCT CASE WHEN sa.status='green' THEN sa.lessonid END) AS green_count,
                COUNT(DISTINCT CASE WHEN sa.status='yellow' THEN sa.lessonid END) AS yellow_count,
                COUNT(DISTINCT CASE WHEN sa.status='red' THEN sa.lessonid END) AS red_count,
                COUNT(DISTINCT sa.lessonid) AS total,
                CASE 
                    WHEN COUNT(DISTINCT sa.lessonid) > 0 THEN 
                        ROUND((COUNT(DISTINCT CASE WHEN sa.status='green' THEN sa.lessonid END)::decimal / COUNT(DISTINCT sa.lessonid)) * 100, 2)
                    ELSE 0 
                END AS quality_percent,
                CASE 
                    WHEN COUNT(DISTINCT sa.lessonid) > 0 THEN 
                        ROUND(((COUNT(DISTINCT CASE WHEN sa.status IN ('green','yellow') THEN sa.lessonid END)::decimal / COUNT(DISTINCT sa.lessonid)) * 100), 2)
                    ELSE 0 
                END AS attendance_percent
            FROM users u
            LEFT JOIN students_groups sg ON u.id = sg.student_id
            LEFT JOIN groups g ON sg.group_id = g.group_id
            LEFT JOIN student_attendance sa ON u.uin = sa.uin
            LEFT JOIN lessons l ON sa.lessonid = l.lessonid
            WHERE u.role='student' {date_condition} {teacher_condition}
        """

        # Фильтр по группе
        if group_name:
            conditions.append("""
                EXISTS (
                    SELECT 1 FROM students_groups sgg2
                    JOIN groups gg ON sgg2.group_id = gg.group_id
                    WHERE sgg2.student_id = u.id AND gg.group_name = %(group_name)s
                )
            """)
            params['group_name'] = group_name

        # Фильтр по курсу
        if course_name:
            conditions.append("""
                EXISTS (
                    SELECT 1 FROM students_groups sgg3
                    JOIN groups gg2 ON sgg3.group_id = gg2.group_id
                    WHERE sgg3.student_id = u.id AND gg2.course = %(course_name)s
                )
            """)
            params['course_name'] = course_name

        # Добавление дополнительных условий фильтрации
        if conditions:
            sql += " AND " + " AND ".join(conditions)

        # Группировка и сортировка
        sql += """
            GROUP BY u.id
            ORDER BY u.last_name, u.first_name
        """

        try:
            self.__cur.execute(sql, params)
            rows = self.__cur.fetchall() or []
            return rows
        except Exception as e:
            print(f'Ошибка при получении фильтрованного рейтинга: {e}')
            return []





    def get_all_teachers(self):
            self.__cur.execute("SELECT DISTINCT teacher as teacher_name FROM lessons WHERE teacher IS NOT NULL ORDER BY teacher;")
            rows = self.__cur.fetchall() or []
            return rows

    # ----------------- Для главной
    def get_total_teachers(self):
        sql = """
            SELECT COUNT(*) AS total_teachers
            FROM users u
            WHERE u.role = 'teacher';
        """
        try:
            self.__cur.execute(sql)
            result = self.__cur.fetchone()
            return result['total_teachers'] if result else 0
        except Exception as e:
            print(f'Ошибка при получении количества преподавателей: {e}')
            return 0

    def get_total_students(self):
        sql = """
            SELECT COUNT(*) AS total_students
            FROM users u
            WHERE u.role = 'student';
        """
        try:
            self.__cur.execute(sql)
            result = self.__cur.fetchone()
            return result['total_students'] if result else 0
        except Exception as e:
            print(f'Ошибка при получении количества студентов: {e}')
            return 0
    def get_total_groups(self):
        sql = "SELECT COUNT(*) AS total_groups FROM groups;"
        try:
            self.__cur.execute(sql)
            result = self.__cur.fetchone()
            return result['total_groups'] if result else 0
        except Exception as e:
            print(f'Ошибка при получении количества групп: {e}')
            return 0
    def get_total_classrooms(self):
        sql = "SELECT COUNT(*) AS total_classrooms FROM AUDIENCES;"
        try:
            self.__cur.execute(sql)
            result = self.__cur.fetchone()
            return result['total_classrooms'] if result else 0
        except Exception as e:
            print(f'Ошибка при получении количества аудиторий: {e}')
            return 0
    def get_weekly_attendance_summary(self):
        sql = """
            SELECT
                COUNT(CASE WHEN r_student.role_name = 'Студент' AND sa.status_id IN(1,2) THEN sa.user_id END) AS present,
                COUNT(CASE WHEN r_student.role_name = 'Студент' AND sa.status_id IN (3, 4) THEN sa.user_id END) AS absent
            FROM student_attendance sa
            JOIN users u_student ON sa.user_id = u_student.user_id
            JOIN roles r_student ON u_student.role_id = r_student.role_id
            JOIN lessons l ON sa.lesson_id = l.lesson_id
            WHERE 
                l.starttime >= CURRENT_DATE - INTERVAL '7 days'
                AND r_student.role_name = 'С��удент'
        """
        try:
            self.__cur.execute(sql)
            result = self.__cur.fetchone()
            present = result['present'] or 0
            absent = result['absent'] or 0
            return {'present': present, 'absent': absent}
        except Exception as e:
            print(f'Ошибка при получении еженедельной сводки посещаемости: {e}')
            return {'present': 0, 'absent': 0}
    def get_activity_data(self):
        sql = """
            SELECT 
                TO_CHAR(l.starttime, 'FMDay') AS day,
                COUNT(CASE WHEN sa.status_id IN (1,2) THEN sa.user_id END) AS present_count
            FROM lessons l
            LEFT JOIN student_attendance sa ON l.lesson_id = sa.lesson_id
            LEFT JOIN users u_student ON sa.user_id = u_student.user_id
            LEFT JOIN roles r_student ON u_student.role_id = r_student.role_id
            WHERE 
                l.starttime >= CURRENT_DATE - INTERVAL '7 days'
                AND r_student.role_name = 'Студент'
            GROUP BY day
            ORDER BY 
                CASE 
                    WHEN TO_CHAR(l.starttime, 'FMDay') ILIKE 'Monday' THEN 1
                    WHEN TO_CHAR(l.starttime, 'FMDay') ILIKE 'Tuesday' THEN 2
                    WHEN TO_CHAR(l.starttime, 'FMDay') ILIKE 'Wednesday' THEN 3
                    WHEN TO_CHAR(l.starttime, 'FMDay') ILIKE 'Thursday' THEN 4
                    WHEN TO_CHAR(l.starttime, 'FMDay') ILIKE 'Friday' THEN 5
                    WHEN TO_CHAR(l.starttime, 'FMDay') ILIKE 'Saturday' THEN 6
                    WHEN TO_CHAR(l.starttime, 'FMDay') ILIKE 'Sunday' THEN 7
                    ELSE 8
                END;
        """
        try:
            self.__cur.execute(sql)
            results = self.__cur.fetchall() or []
            labels = [result['day'] for result in results]
            values = [result['present_count'] for result in results]
            return {'labels': labels, 'values': values}
        except Exception as e:
            print(f'Ошибка при получении данных активности студентов: {e}')
            return {'labels': [], 'values': []}

    # график
    def get_all_graphs(self):
        sql = """
            SELECT 
                graph_id, 
                course, 
                graph_name, 
                start_date, 
                end_date
            FROM 
                graph
            ORDER BY 
                course ASC, 
                start_date ASC
        """
        try:
            self.__cur.execute(sql)
            return self.__cur.fetchall() or []
        except Exception as e:
            print(f'Ошибка при получении графиков: {e}')
            return []

    def add_graph(self, course, graph_name, start_date, end_date):
        sql = """
            INSERT INTO graph (course, graph_name, start_date, end_date)
            VALUES (%s, %s, %s, %s)
        """
        try:
            self.__cur.execute(sql, (course, graph_name, start_date, end_date))
            self.__db.commit()
            return True
        except Exception as e:
            self.__db.rollback()
            print(f'Ошибка при добавлении графика: {e}')
            return False

    def delete_graphs(self, graph_ids):
        sql = "DELETE FROM graph WHERE graph_id = ANY(%s::int[])"
        try:
            self.__cur.execute(sql, (graph_ids,))
            self.__db.commit()
            return True
        except Exception as e:
            self.__db.rollback()
            print(f'Ошибка при удалении графиков: {e}')
            return False
    # -------------------- Студенты
    def add_student(self, first_name, last_name, patronymic, birthday, phone_number, password, uin):
        sql = """
            INSERT INTO users (first_name, last_name, patronymic, birthday, phone_number, password, uin, role)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'student')
        """
        try:
            self.__cur.execute(sql, (first_name, last_name, patronymic, birthday, phone_number, password, uin))
            self.__db.commit()
            return True
        except Exception as e:
            self.__db.rollback()
            print(f'Ошибка при добавлении студента: {e}')
            return False

    def get_student_details(self, uin):
        sql = """
            SELECT 
                u.uin,
                u.id,
                u.first_name,
                u.last_name,
                u.patronymic,
                u.phone_number,
                string_agg(g.group_name, ' / ') AS group_names,
                array_agg(g.group_id) AS group_ids,
                u.uin as login
            FROM users u
            LEFT JOIN students_groups sg ON u.id = sg.student_id
            LEFT JOIN groups g ON sg.group_id = g.group_id
            WHERE u.uin = %s AND u.role = 'student'
            GROUP BY u.id, u.first_name, u.last_name, u.patronymic, u.phone_number
        """
        try:
            self.__cur.execute(sql, (uin,))
            return self.__cur.fetchone()
        except Exception as e:
            print(f'Ошибка при получении деталей студента {uin}: {e}')
            return None


    def update_student(self, uin, group_ids=None, phone_number=None):
        params = []
        set_clauses = []
        
        if phone_number is not None:
            set_clauses.append('phone_number = %s')
            params.append(phone_number)
        
        if set_clauses:
            sql = f"UPDATE users SET {', '.join(set_clauses)} WHERE uin = %s AND role = 'student'"
            params.append(uin)
            try:
                self.__cur.execute(sql, tuple(params))
            except Exception as e:
                self.__db.rollback()
                print(f'Ошибка при обновлении данных студента {uin}: {e}')
                return False
        
        if group_ids is not None:
            try:
                # Удаляем старые записи
                delete_sql = "DELETE FROM students_groups WHERE student_id = (SELECT id FROM users WHERE uin = %s)"
                self.__cur.execute(delete_sql, (uin,))
                
                # Добавляем новые записи
                insert_sql = "INSERT INTO students_groups (student_id, group_id) VALUES ((SELECT id FROM users WHERE uin = %s), %s)"
                for group_id in group_ids:
                    self.__cur.execute(insert_sql, (uin, group_id))
                
                self.__db.commit()
                return True
            except Exception as e:
                self.__db.rollback()
                print(f'Ошибка при обновлении групп студента {uin}: {e}')
                return False
        else:
            self.__db.commit()
            return True


    def delete_students(self, uin_list):
        sql = "DELETE FROM users WHERE uin = ANY(%s::text[]) AND role = 'student'"
        print(uin_list)
        try:
            self.__cur.execute(sql, (uin_list,))
            self.__db.commit()
            return True
        except Exception as e:
            self.__db.rollback()
            print(f'Ошибка при удалении студентов: {e}')
            return False

    def get_student_attendance(self, uin):
        sql = """
            SELECT 
                l.starttime::date AS date,
                TO_CHAR(l.starttime, 'HH24:MI') AS start_time,
                TO_CHAR(sa.scantime, 'HH24:MI') AS marked_time,
                l.description AS subject,
                l.teacher,
                sa.status
            FROM student_attendance sa
            JOIN lessons l ON sa.lessonid = l.lessonid
            WHERE sa.uin = %s AND STATUS IN ('red','yellow')
            ORDER BY l.starttime DESC
        """
        try:
            self.__cur.execute(sql, (uin,))
            return self.__cur.fetchall() or []
        except Exception as e:
            print(f'Ошибка при получении посещаемости студента {uin}: {e}')
            return []

    def get_groups(self):
        sql = "SELECT group_id, group_name FROM groups"
        try:
            self.__cur.execute(sql)
            return self.__cur.fetchall() or []
        except Exception as e:
            print(f'Ошибка при получении групп: {e}')
            return []

    def get_employee_details(self, user_id):
        """
        Возвращает информацию о сотруднике, включая:
        - total_lessons_count (считаем, сколько записей в lessons, где teacheruin = uin),
        - late_count, absent_count (считаем только те "yellow"/"red", у которых есть запись в lesson_creation_times).
        """
        sql_base = """
            SELECT 
                u.id,
                u.first_name,
                u.last_name,
                u.patronymic,
                u.phone_number,
                u.role,
                u.uin as login,
                string_agg(DISTINCT s.subject_name, ' / ') AS subjects,
                string_agg(DISTINCT g.group_name, ' / ') AS groups,

                -- Эти два поля ниже мы фактически не используем, но оставим для наглядности
                COALESCE(att.late_count, 0)   AS old_late_count,  
                COALESCE(att.absent_count, 0) AS old_absent_count

            FROM users u
            LEFT JOIN subjects_teachers st ON u.id = st.teacher_id
            LEFT JOIN subjects s         ON st.subject_id = s.subject_id
            LEFT JOIN groups   g         ON u.id = g.curator_id

            -- Подзапрос, где мы считаем late_count и absent_count
            LEFT JOIN (
                SELECT 
                    l.teacheruin,

                    /* 
                    Считаем "yellow", но только если в lesson_creation_times есть запись,
                    то есть lct.lessonid IS NOT NULL.
                    */
                    COUNT(
                    DISTINCT CASE 
                        WHEN sa.status = 'yellow' AND lct.lessonid IS NOT NULL
                        THEN l.lessonid
                    END
                    ) AS late_count,

                    /*
                    То же для "red": только если lesson_creation_times есть, считаем пропуск
                    */
                    COUNT(
                    DISTINCT CASE 
                        WHEN sa.status = 'red' AND lct.lessonid IS NOT NULL
                        THEN l.lessonid
                    END
                    ) AS absent_count

                FROM lessons l
                LEFT JOIN student_attendance sa
                    ON l.lessonid = sa.lessonid
                LEFT JOIN lesson_creation_times lct
                    ON l.lessonid = lct.lessonid
                GROUP BY l.teacheruin
            ) att ON att.teacheruin = u.uin

            WHERE u.id = %s 
            AND u.role != 'student'
            GROUP BY 
                u.id, u.first_name, u.last_name, u.patronymic, 
                u.phone_number, u.role, u.uin,
                att.late_count, att.absent_count
        """

        # Чтобы найти total_lessons_count, используем teacheruin:
        sql_teacher_uin = "SELECT uin FROM users WHERE id = %s"

        # Сколько всего уроков у преподавателя (просто считаем записи в lessons по teacheruin):
        sql_lessons_count = """
            SELECT COUNT(*) AS total_lessons_count
            FROM lessons
            WHERE teacheruin = %s
        """

        try:
            # 1) Основной запрос с left join'ами
            self.__cur.execute(sql_base, (user_id,))
            employee = self.__cur.fetchone()
            if not employee:
                return None

            # 2) Нужно достать uin препода:
            self.__cur.execute(sql_teacher_uin, (user_id,))
            row_uin = self.__cur.fetchone()
            if not row_uin:
                # Если почему-то нет, ставим 0
                employee['total_lessons_count'] = 0
                return employee

            teacher_uin = row_uin['uin']

            # 3) Подсчитываем общее количество уроков для этого teacher_uin
            self.__cur.execute(sql_lessons_count, (teacher_uin,))
            row_count = self.__cur.fetchone()
            if row_count:
                employee['total_lessons_count'] = row_count['total_lessons_count']
            else:
                employee['total_lessons_count'] = 0

            return employee

        except Exception as e:
            print(f'Ошибка при получении деталей сотрудника {user_id}: {e}')
            return None




    def get_employee_attendance(self, user_id):
        sql = """
            SELECT 
                l.starttime::date AS date,
                TO_CHAR(l.starttime, 'HH24:MI') AS start_time,
                TO_CHAR(sa.scantime, 'HH24:MI') AS marked_time,
                l.description AS subject,
                l."group" AS group_name,
                sa.status
            FROM lessons l
            JOIN student_attendance sa ON l.lessonid = sa.lessonid
            JOIN users u ON sa.uin = u.uin
            WHERE u.id = %s AND sa.status IN ('red', 'yellow')
            ORDER BY l.starttime DESC
        """
        try:
            self.__cur.execute(sql, (user_id,))
            return self.__cur.fetchall() or []
        except Exception as e:
            print(f'Ошибка при получении посещаемости сотрудника {user_id}: {e}')
            return []
