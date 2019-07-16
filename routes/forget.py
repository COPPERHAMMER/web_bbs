import uuid
from flask import (render_template,
                   request,
                   flash,
                   redirect,
                   Blueprint,
                   url_for,
                   )

from config import admin_mail
from models.message import send_mail
from models.user import User
from routes.myredis import user_identify_cache

main = Blueprint('forget', __name__)


@main.route('/')
# 点击忘记密码后，跳转到此页面输入注册邮箱。
def forget():
    return render_template('forget/forget.html')


@main.route('/', methods=['POST'])
# 处理POST请求，发送带token的验证邮件。
def forget_post():
    reset_token = str(uuid.uuid4())
    mail_addr = request.form.get('mail_address').strip()
    print('发送的邮件地址:', mail_addr)
    user = User.one(email=mail_addr)
    if user is not None:
        v = user.id
        key = 'reset_token.{}'.format(reset_token)
        user_identify_cache.set(key, v)
        try:
            send_mail(
                subject='Swordman BBS - 重置密码',
                author=admin_mail,
                to=mail_addr,
                content='请点击以下链接重设密码，如果非您本人操作，请无视本邮件。'
                        '\nhttp://129.28.190.39/forget/reset?token={}'.format(reset_token),
            )

        except ValueError:
            flash('邮箱输入错误，请重新输入。')
            return redirect('/forget')

        else:
            flash('发送成功，请前往邮箱查看。')
            return redirect('/forget')
    else:
        flash('邮箱输入错误，请重新输入。')
        return redirect('/forget')


@main.route('/reset')
# 点击邮件中的连接，用以输入新密码的页面
def forget_reset():
    token = request.args['token']
    key = 'reset_token.{}'.format(token)
    if user_identify_cache.exists(key):
        return render_template('forget/forget_reset.html', token=token, )

    else:
        flash('当前链接失效，请重试')
        return redirect('/forget')


@main.route('/reset', methods=['POST'])
# 提交新密码，执行密码修改的路由
def forget_reset_post():
    token = request.args['token']
    k = 'reset_token.{}'.format(token)
    try:
        if user_identify_cache.exists(k):
            user_id = int(user_identify_cache.get(k))
            new_pass = request.form.get('new_pass')
            if len(new_pass) > 2:
                User.update(user_id, password=User.salted_password(new_pass))
                flash('密码重置成功，请重新登陆')
                return redirect('/')
            else:
                flash("密码重置失败，本链接失效，请重新尝试")
                return redirect(url_for('.forget'))
        else:
            flash('链接失效，请重试')
            redirect(url_for('.forget'))
    finally:
        user_identify_cache.delete(k)
