#! /usr/bin/env python3
import time

from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

import config
import secret
from models.base_model import db
from models.reply import Reply
from models.topic import Topic
from models.user import User
from routes import current_user

# 注册蓝图
# url_prefix 给蓝图中的每个路由加一个前缀
from routes.index import main as index_routes, not_found
from routes.topic import main as topic_routes
from routes.reply import main as reply_routes
from routes.mail import main as mail_routes
from routes.forget import main as forget_routes
from routes.info import main as info_routes
from routes.user import main as user_routes


def count(data):
    return len(data)


def format_time(unix_timestamp):
    f = '%Y-%m-%d %H:%M:%S'
    value = time.localtime(unix_timestamp)
    formatted = time.strftime(f, value)
    return formatted


def how_long_ago(unix_timestamp):
    current_time = time.time()
    k = current_time - unix_timestamp
    if k < 60:
        return '{}秒前'.format(int(k))
    elif k < 3600:
        return '{}分钟前'.format(int(k // 60))
    elif k < 86400:
        return '{}小时前'.format(int(k // 3600))
    elif k < 2592000:
        return '{}天前'.format(int(k // 86400))
    elif k < 31104000:
        return '{}个月前'.format(int(k // 259200))
    else:
        return '{}年前'.format(int(k // 31104000))


def configured_app():
    app = Flask(__name__)
    # 设置 secret_key 来使用 flask 自带的 session
    app.secret_key = config.secret_key
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:{}@localhost/web19?charset=utf8mb4'.format(
        secret.database_password
    )
    db.init_app(app)

    app.register_blueprint(index_routes)
    app.register_blueprint(user_routes)
    app.register_blueprint(forget_routes, url_prefix='/forget')
    app.register_blueprint(topic_routes, url_prefix='/topic')
    app.register_blueprint(reply_routes, url_prefix='/reply')
    app.register_blueprint(mail_routes, url_prefix='/mail')
    app.register_blueprint(info_routes, url_prefix='/info')

    app.template_filter()(count)
    app.template_filter()(format_time)
    app.template_filter()(how_long_ago)

    app.template_global()(current_user)
    app.errorhandler(404)(not_found)

    admin = Admin(app, name='Swordman BBS')
    admin.add_view(ModelView(User, db.session))
    admin.add_view(ModelView(Topic, db.session))
    admin.add_view(ModelView(Reply, db.session))

    return app


if __name__ == '__main__':

    # debug 模式可自动加载对代码的变动, 所以不用重启程序
    # 自动 reload jinja
    app = configured_app()
    # app.config['TEMPLATES_AUTO_RELOAD'] = True
    # app.jinja_env.auto_reload = True
    # app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    config = dict(
        # debug=True,
        host='localhost',
        port=3000,
    )
    app.run(**config)
