import json
import uuid
from functools import wraps

from flask import (request,
                   abort,
                   redirect,
                   flash,
                   )

from config import web_domain_name
from models.info import Info
from models.reply import Reply
from models.session import ServerSession
from models.topic import Topic
from models.user import User

from routes.myredis import (user_identify_cache,
                            cached_topic_id2topic,
                            cached_reply_id2reply,
                            cached_user_id2user, data_cache, )


def current_user():

    session_id = request.cookies.get('session_id')
    key = 'session_id.{}'.format(session_id)

    if session_id is not None and user_identify_cache.exists(key):
        session_json = user_identify_cache.get(key)
        session_dict = json.loads(session_json)
        my_session = ServerSession(session_dict)

        if not my_session.expired():
            user_id = my_session.user_id
            # return User.one(id=user_id)
            return cached_user_id2user(user_id)


def csrf_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.args['token']
        key = 'csrf_token.{}'.format(token)
        u = current_user()
        if user_identify_cache.exists(key):
            uid_from_redis = user_identify_cache.get(key)

            if u.id == int(uid_from_redis):
                user_identify_cache.delete(key)
                return f(*args, **kwargs)
        return abort(401)

    return wrapper


def new_csrf_token():
    u = current_user()
    token = str(uuid.uuid4())
    key = 'csrf_token.{}'.format(token)
    if u is not None:
        user_identify_cache.set(key, u.id)
        user_identify_cache.expire(key, 36000)
    return token


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        u = current_user()
        if u is not None:
            return func(*args, **kwargs)
        else:
            flash('请登录后执行此操作')
            return redirect('/')

    return wrapper


def at_names(content):
    names = []
    if '@' in content:
        s = [t for t in content.split() if len(t) > 1 and t[-1] != "@"]
        for k in s:
            if "@" in k:
                p = k.rfind("@")
                name = k[p + 1:]
                names.append(name)

    return names


def at_users(content):
    users = []
    for n in at_names(content):
        i = User.one(username=n)
        if i is not None:
            users.append(i)
    return users


def inform_at(topic, checked_content, caller):
    # topic:@ 发生的topic
    # check_content:需要检查 @ 发生的文本
    # caller:发送 @ 的用户

    # 检查当前topic中的正文或评论中是否有用户使用@功能，有的话则发站内信提醒被@的用户。
    called_users = at_users(checked_content)
    with data_cache.pipeline(transaction=False) as pipe:
        for called_user in called_users:
            Info.send(title='{}@了你，快去看看吧。'.format(caller.username),
                      content='用户{}@了你，点击{}/topic/{}查看。'
                      .format(caller.username, web_domain_name, topic.id),
                      receiver_id=called_user.id)
            key = 'user_id_{}.received_info'.format(called_user.id)
            pipe.delete(key)
        pipe.execute()


def topic_owner_required_post(func):
    # POST: 检验topic主人的id是否和当前操作者的id相同
    @wraps(func)
    def wrapper(*args, **kwargs):
        u = current_user()
        topic_id = request.form.get('topic_id', '')
        # t: Topic = Topic.one(id=topic_id)
        t: Topic = cached_topic_id2topic(topic_id)

        if t is not None and u.id == t.user_id:
            return func(*args, **kwargs)
        else:
            return abort(404)

    return wrapper


def reply_owner_required_post(func):
    # POST: 操作Reply时，检验当前操作者否有权限执行操作
    @wraps(func)
    def wrapper(*args, **kwargs):
        u = current_user()
        reply_id = request.form.get('reply_id', '')
        # r: Reply = Reply.one(id=reply_id)
        r: Reply = cached_reply_id2reply(reply_id)
        # t = Topic.one(id=r.topic_id)
        t = cached_topic_id2topic(r.topic_id)
        if r is not None:
            if u.id == r.user_id or u.id == t.user_id:
                # 要么是话题作者，要么是回复作者
                return func(*args, **kwargs)
        return abort(404)

    return wrapper
