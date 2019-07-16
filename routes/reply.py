from flask import (
    request,
    redirect,
    url_for,
    Blueprint,
    flash,
    abort, )

from config import web_domain_name
from models.info import Info
from models.topic import Topic
from routes import (reply_owner_required_post,
                    current_user,
                    csrf_required,
                    login_required,
                    inform_at,
                    cached_topic_id2topic,
                    cached_reply_id2reply,
                    )

from models.reply import Reply
from routes.myredis import data_cache

main = Blueprint('my_reply', __name__)


@main.route('', methods=['POST'])
@login_required
@csrf_required
def add():
    form = request.form.to_dict()
    author = current_user()
    author_id = author.id
    form['user_id'] = author_id
    new_rep = Reply.new(form)

    # 有新的回复时，更新帖子的last_active_time
    t: Topic = Topic.one(id=new_rep.topic_id)
    t.last_active_time = new_rep.created_time
    t.last_rep_uid = author_id
    t.reps = t.reps + 1
    t.save()

    with data_cache.pipeline(transaction=False) as pipe:
        key = 'topic_id_{}.replies'.format(t.id)
        key2 = 'topic_id_{}.topic_info'.format(t.id)
        pipe.delete(key)
        pipe.delete(key2)
        pipe.execute()

    inform_at(t, new_rep.content, author)
    if author.id != t.user_id:
        # 如果是回复他人的帖子，则对主题主人发系统信息通知
        Info.send(title='{}刚刚回复了您的主题'.format(author.username),
                  receiver_id=t.user_id,
                  content='{}在您的主题{} 中发表了一个新回复,查看：\n\r{}/topic/{}'
                  .format(author.username, t.title, web_domain_name, t.id))
        key = 'user_id_{}.received_info'.format(t.user_id)
        data_cache.delete(key)

    return redirect(url_for('my_topic.detail', topic_id=new_rep.topic_id))


@main.route('/deletion', methods=['POST'])
@reply_owner_required_post
@csrf_required
# 先验证token, 再验证权限（是帖主或回复人）
def delete():
    i = int(request.form.get('reply_id', -1))
    rep: Reply = Reply.one(id=i)
    if rep is None:
        return abort(404)
    topic: Topic = Topic.one(id=rep.topic_id)
    Reply.delete(rep)
    with data_cache.pipeline(transaction=False) as pipe:
        key = 'topic_id_{}.replies'.format(topic.id)
        key2 = 'topic_id_{}.topic_info'.format(topic.id)
        pipe.delete(key)
        pipe.delete(key2)
        pipe.execute()

    # 更新帖子的last_active_time
    last_rep = topic.last_reply()
    topic.last_active_time = last_rep.created_time if last_rep is not None else topic.created_time
    topic.reps = topic.reps - 1
    topic.save()

    flash('回复删除成功')
    return redirect(url_for('my_topic.detail', topic_id=topic.id))
