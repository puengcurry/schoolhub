from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=80)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=4)])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class AskForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Ask')

class AnswerForm(FlaskForm):
    content = TextAreaField('Answer', validators=[DataRequired()])
    submit = SubmitField('Submit Answer')

class TaskForm(FlaskForm):
    subject = StringField('Subject', validators=[DataRequired()], render_kw={"class": "form-input"})
    title = StringField('Title', validators=[DataRequired()], render_kw={"class": "form-input"})
    due_date = StringField('Due date', validators=[DataRequired()], render_kw={"class": "form-input"})
    submit = SubmitField('Add Task')