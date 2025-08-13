import os
from flask import Flask, render_template, redirect, url_for, request, flash, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import Config
from models import db, User, Question, Answer, Task
from forms import RegisterForm, LoginForm, AskForm, AnswerForm, TaskForm


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# DB 생성용(최초 한 번 실행)
# 이 코드는 애플리케이션 시작 시 한 번 실행됩니다.
with app.app_context():
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    db.create_all()


# 간단한 로그인 데코레이터
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('로그인이 필요합니다.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated


@app.route('/')
def index():
    questions = Question.query.order_by(Question.created_at.desc()).all()
    # 로그인한 사용자 목록을 가져와서 템플릿으로 전달합니다.
    logged_in_users = User.query.filter_by(is_logged_in=True).all()
    return render_template('index.html', questions=questions, logged_in_users=logged_in_users)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('이미 있는 아이디입니다.')
            return redirect(url_for('register'))
        user = User(username=form.username.data,
                    password_hash=generate_password_hash(form.password.data))
        db.session.add(user)
        db.session.commit()
        flash('회원가입 완료. 로그인하세요.')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            session['user_id'] = user.id
            session['username'] = user.username

            # 로그인 상태 업데이트
            user.is_logged_in = True
            db.session.commit()

            flash('로그인 성공')
            return redirect(url_for('index'))
        flash('아이디/비밀번호가 틀렸습니다.')
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    # 로그인 상태 업데이트
    user = User.query.get(session.get('user_id'))
    if user:
        user.is_logged_in = False
        db.session.commit()

    session.clear()
    flash('로그아웃 되었습니다.')
    return redirect(url_for('index'))


@app.route('/ask', methods=['GET', 'POST'])
@login_required
def ask():
    form = AskForm()
    if form.validate_on_submit():
        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(path)
                image_filename = filename
        q = Question(user_id=session['user_id'],
                     title=form.title.data, content=form.content.data, image=image_filename)
        db.session.add(q)
        db.session.commit()
        flash('질문이 등록되었습니다.')
        return redirect(url_for('index'))
    return render_template('ask.html', form=form)


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/question/<int:q_id>', methods=['GET', 'POST'])
def question_detail(q_id):
    q = Question.query.get_or_404(q_id)
    form = AnswerForm()
    if form.validate_on_submit():
        a = Answer(question_id=q.id, user_id=session.get('user_id', None) or 0,
                   content=form.content.data)
        db.session.add(a)
        db.session.commit()
        flash('답변 등록됨')
        return redirect(url_for('question_detail', q_id=q.id))
    return render_template('question.html', question=q, form=form)


@app.route('/accept_answer/<int:answer_id>')
@login_required
def accept_answer(answer_id):
    a = Answer.query.get_or_404(answer_id)
    q = a.question
    # 질문자만 채택 가능
    if q.user_id != session['user_id']:
        flash('질문자만 채택할 수 있습니다.')
        return redirect(url_for('question_detail', q_id=q.id))
    # 이미 채택된 답변 해제(간단 처리)
    other = Answer.query.filter_by(question_id=q.id, is_accepted=True).first()
    if other:
        other.is_accepted = False
        # 포인트 환원(간단히 차감)
        user_other = User.query.get(other.user_id)
        if user_other:
            user_other.points = max(0, user_other.points - 5)
    a.is_accepted = True
    user = User.query.get(a.user_id)
    if user:
        user.points += 10  # 채택되면 10포인트 지급
    db.session.commit()
    flash('답변 채택 완료')
    return redirect(url_for('question_detail', q_id=q.id))


# Tasks (과제/시험 관리)
@app.route('/tasks', methods=['GET', 'POST'])
@login_required
def tasks():
    form = TaskForm()
    if form.validate_on_submit():
        t = Task(user_id=session['user_id'], subject=form.subject.data,
                 title=form.title.data, due_date=form.due_date.data)
        db.session.add(t)
        db.session.commit()
        flash('과제 추가됨')
        return redirect(url_for('tasks'))
    user_tasks = Task.query.filter_by(user_id=session['user_id']).all()
    return render_template('tasks.html', tasks=user_tasks, form=form)


@app.route('/toggle_task/<int:task_id>')
@login_required
def toggle_task(task_id):
    t = Task.query.get_or_404(task_id)
    if t.user_id != session['user_id']:
        flash('권한 없음')
        return redirect(url_for('tasks'))
    t.is_done = not t.is_done
    db.session.commit()
    return redirect(url_for('tasks'))


# 성적 분석기 (간단)
@app.route('/grades', methods=['GET', 'POST'])
@login_required
def grades():
    result = None
    if request.method == 'POST':
        # form expects: score1, weight1, score2, weight2, target_grade(평균기준)
        try:
            s1 = float(request.form.get('score1', 0))
            w1 = float(request.form.get('weight1', 0)) / 100
            s2 = float(request.form.get('score2', 0))
            w2 = float(request.form.get('weight2', 0)) / 100
            current = s1 * w1 + s2 * w2
            target = float(request.form.get('target', 90))  # 예: 90점 A
            # 만약 다음 시험(지필)에서 필요한 점수 x 를 구하려면: current_without_future + x*future_weight >= target
            future_weight = float(request.form.get('future_weight', 0)) / 100
            # assume s1 is 수행, s2 is 지필 so compute required next 점수 if needed
            # 여기서는 일반적 형태로: cur = known; need x so that known + x*future_weight >= target
            known = current
            if future_weight == 0:
                need = None
            else:
                need = (target - known) / future_weight
                need = max(0, min(100, need))
            result = {'current': round(current, 2), 'need': round(need, 2) if need is not None else None}
        except Exception as e:
            flash('입력 형식 오류: 숫자를 확인하세요.')
    return render_template('grades.html', result=result)


if __name__ == '__main__':
    app.secret_key = app.config['SECRET_KEY']
    app.run(debug=True, host='0.0.0.0', port=5001)