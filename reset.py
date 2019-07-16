import redis
from sqlalchemy import create_engine

import secret
from app import configured_app
from models.base_model import db
from models.board import Board
from models.topic import Topic
from models.user import User
from models.reply import Reply
from models.message import Messages
from models.info import Info


def reset_database():
    url = 'mysql+pymysql://root:{}@localhost/?charset=utf8mb4'.format(
        secret.database_password
    )
    e = create_engine(url, echo=True)

    with e.connect() as c:
        c.execute('DROP DATABASE IF EXISTS web19')
        c.execute('CREATE DATABASE web19 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
        c.execute('USE web19')

    db.metadata.create_all(bind=e)


def generate_fake_date():
    form_admin_user = dict(
        username='test',
        password='123',
        email='guojiannan@swordmaan.club',
        signature='欢迎来到小破站'
    )
    User.register(form_admin_user)

    form1 = dict(
        username='Swordman',
        password='123',
        email='296731051@qq.com',
    )

    form2 = dict(
        username='gua',
        password='123',
        email='cantrip@qq.com',
    )
    User.register(form2)
    u = User.register(form1)
    Board.new({'title': '问答'})
    Board.new({'title': '资讯'})
    share_board = Board.new(dict(title='分享'))
    with open('markdown_demo.md', encoding='utf8') as f:
        content = f.read()

    form = dict(
        title='markdown demo',
        board_id=share_board.id,
        content=content
    )
    Topic.add(form, u.id)

    topics = [dict(
        title='测试板块{}'.format(x),
        board_id=x,
        content='测试板块{}'.format(x),
    ) for x in range(1, 4)]

    for t in topics:
        Topic.add(t, 1)

    with open('update_log.txt', encoding='utf-8') as f:
        update_log = f.read()

    form_update_log = dict(
        title='更新日志',
        board_id=share_board.id,
        content=update_log,
    )
    Topic.add(form_update_log, u.id)


if __name__ == '__main__':
    app = configured_app()
    with app.app_context():
        reset_database()
        generate_fake_date()

    cache1 = redis.StrictRedis()
    cache1.flushdb()

    cache2 = redis.StrictRedis(db=1)
    cache2.flushdb()
