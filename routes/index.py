import json
from random import randint

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    Blueprint,
    flash, make_response,
)

from config import admin_mail
from models.message import send_mail
from models.session import ServerSession
from models.user import User
from routes import current_user
from routes.myredis import user_identify_cache

main = Blueprint('index', __name__)


@main.route('/')
def index():
    if current_user() is not None:
        return redirect(url_for('my_topic.index'))
    return render_template('index/index.html')


@main.route('/login_page')
def login_page():
    return render_template('index/index.html')


@main.route('/register')
def register():
    email = request.args.get('email', None)
    if email is None:
        return redirect('/')
    return render_template('index/register.html', email=email)


@main.route('/register/captcha', methods=['POST'])
# 发送包含注册验证码的邮件，跳转到输用户名，验证码，密码的界面
def register_check_mail():
    email = request.form.get('email', '')
    u = User.one(email=email)
    if u is None:
        verify_code = ''.join([str(randint(0, 9)) for _ in range(6)])
        user_identify_cache.set(email, verify_code, 600)
        title = '欢迎注册Swordman BBS'
        content = '欢迎注册Swordman BBS。您的验证码为{}，' \
                  '如果不是您本人的操作，请无视本邮件。'.format(verify_code)
        try:
            send_mail(
                subject=title,
                author=admin_mail,
                to=email,
                content=content, )
            flash('验证码已发送至您的邮箱，请查收。')
            return redirect(url_for('.register', email=email))

        except ValueError:
            flash('邮箱已被注册或邮箱格式错误')
            return redirect('/')
    else:
        flash('邮箱已被注册或邮箱格式错误')
        return redirect('/')


@main.route('/register', methods=['POST'])
def register_post():
    form = request.form.to_dict()
    verify_code = form.pop('verify_code', '')
    email = form.get('email', '')
    if user_identify_cache.exists(email) and int(user_identify_cache.get(email)) == int(verify_code):
        u = User.register(form)
        if u is not None:
            flash('用户{}注册成功，请登录'.format(u.username))
            user_identify_cache.delete(email)
            return redirect('/')
        else:
            return redirect(request.referrer)

    else:
        flash('无效的验证码，请重试')
        return redirect(request.referrer)


@main.route('/login', methods=['POST'])
def login_post():
    form = request.form
    u = User.validate_login(form)
    if u is None:
        flash('用户名或密码错误')
        return redirect(url_for('index.index'))
    else:
        # 使用flask版本的客户端session:
        # session['user_id'] = u.id
        # # 设置 cookie 有效期为 永久
        # session.permanent = True
        # return redirect(url_for('gua_topic.index'))

        # 使用redis实现服务端session:
        response = make_response(redirect(url_for('my_topic.index')))
        user_session = ServerSession.new(u.id)
        response.headers['Set-Cookie'] = 'session_id=' + user_session.session_id
        key = 'session_id.{}'.format(user_session.session_id)
        user_identify_cache.set(key, json.dumps(user_session.todict()))

        return response


def not_found(e):
    return render_template('404.html')


@main.route('/logout')
def logout():
    session_id = request.cookies.get('session_id')
    key = 'session_id.{}'.format(session_id)
    if session_id is not None and user_identify_cache.exists(key):
        user_identify_cache.delete(key)
    return redirect('/')