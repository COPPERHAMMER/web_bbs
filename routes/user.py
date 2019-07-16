import os
import uuid

from flask import (render_template,
                   abort,
                   request,
                   flash,
                   redirect,
                   url_for,
                   send_from_directory,
                   Blueprint,
                   )

from werkzeug.datastructures import FileStorage

from models.reply import Reply
from models.topic import Topic
from models.user import User
from routes import (login_required,
                    current_user,
                    new_csrf_token,
                    csrf_required,
                    cached_topic_id2topic,
                    cached_user_id2user,
                    )
from routes.myredis import (cached_created_topics,
                            cached_replied_topics,
                            data_cache,
                            )

main = Blueprint('my_user', __name__)


@main.route('/profile')
@login_required
def profile():
    """用户的个人主页"""
    u = current_user()
    visitor_id = u.id
    recent_create_topics = Topic.newest_n(5, user_id=visitor_id)
    replies = Reply.newest_n(user_id=visitor_id)
    recent_rep_topics = []
    for rep in replies:
        topic = cached_topic_id2topic(rep.topic_id)
        if topic not in recent_rep_topics:
            recent_rep_topics.append(topic)
        if len(recent_rep_topics) >= 5:
            break

    return render_template('user/user_profile.html',
                           user=u,
                           recent_rep_topics=recent_rep_topics,
                           recent_create_topics=recent_create_topics,
                           visitor_id=visitor_id)


@main.route('/user/<user_id>')
def user_detail(user_id):
    """访问其他用户"""
    u = cached_user_id2user(user_id)
    visitor = current_user()
    if u is None:
        return abort(404)
    else:
        recent_create_topics = Topic.newest_n(5, user_id=user_id)
        replies = Reply.newest_n(user_id=user_id)
        recent_rep_topics = []
        for rep in replies:
            topic = cached_topic_id2topic(rep.topic_id)
            if topic not in recent_rep_topics:
                recent_rep_topics.append(topic)
            if len(recent_rep_topics) >= 5:
                break

        return render_template('user/user_profile.html',
                               user=u,
                               visitor=visitor,
                               recent_rep_topics=recent_rep_topics,
                               recent_create_topics=recent_create_topics,
                               )


@main.route('/user/<user_id>/topics/')
def user_created_topics(user_id):
    """查看用户发表的所有帖子"""
    u = cached_user_id2user(user_id)
    if u is None:
        abort(404)
    else:
        topics = cached_created_topics(user_id)
        topics.sort(key=lambda x: x.last_active_time, reverse=True)
        return render_template('user/user_items.html',
                               itemtype='创建',
                               topics=topics,
                               user=u,
                               )


@main.route('/user/<user_id>/replies/')
def user_replied_topics(user_id):
    """查看用户回复过的所有帖子"""
    u = cached_user_id2user(user_id)
    if u is None:
        abort(404)
    else:
        # replies = Reply.all(user_id=id)
        #
        # topics = []
        # if replies:
        #     for rep in replies:
        #         topic = Topic.one(id=rep.topic_id)
        #         if topic not in topics:
        #             topics.append(topic)
        #     topics.sort(key=lambda x: x.last_active_time, reverse=True)
        topics = cached_replied_topics(user_id)
        return render_template('user/user_items.html',
                               itemtype='参与',
                               topics=topics,
                               user=u,
                               )


@main.route('/setting')
@login_required
def setting():
    """设置页面"""
    u = current_user()
    token = new_csrf_token()
    return render_template('user/setting.html', user=u, token=token)


@main.route('/setting', methods=['POST'])
@login_required
@csrf_required
def setting_post():
    """提交更改"""
    u = current_user()
    form = request.form.to_dict()

    if form['action'] == 'change_password':  # 如果用户点击的是更改密码
        new_pass = form['new_pass']

        if u.password == User.salted_password(form['old_pass']):
            if len(new_pass) <= 2:
                flash('密码强度过低，请重新输入')
            else:
                User.update(u.id, password=User.salted_password(new_pass))
                key = 'user_id_{}.user_info'.format(u.id)
                data_cache.delete(key)
                flash('密码修改成功')
        else:
            flash('密码错误，请重新输入')

    elif form['action'] == 'change_settings':
        # 如果用户点击的是更改设置，修改同步到数据库，并清理redis失效缓存
        new_name = form['name']
        if new_name != u.username:  # 如果修改了用户名，需要检测新用户名是否被占用
            if User.one(username=new_name) is None:
                User.update(u.id, username=new_name, signature=form['signature'])
                key = 'user_id_{}.user_info'.format(u.id)
                data_cache.delete(key)
                flash('个人资料修改成功')
            else:
                flash('用户名被占用，请重新输入')
        else:  # 如果没修改用户名
            User.update(u.id, signature=form['signature'])
            key = 'user_id_{}.user_info'.format(u.id)
            data_cache.delete(key)
            flash('个人资料修改成功')

    return redirect(url_for('.setting'))


@main.route('/image/avatar', methods=['POST'])
@login_required
@csrf_required
def avatar_set():
    """设置头像"""
    u = current_user()
    file: FileStorage = request.files['avatar']
    filename = 'avatar_uid=[{}]'.format(u.id)+str(uuid.uuid4())
    path = os.path.join('images', filename)
    file.save(path)
    User.update(u.id, image='/images/{}'.format(filename))
    key = 'user_id_{}.user_info'.format(u.id)
    data_cache.delete(key)
    return redirect(url_for('.profile'))


@main.route('/images/<filename>')
def image(filename):
    return send_from_directory('images', filename)
