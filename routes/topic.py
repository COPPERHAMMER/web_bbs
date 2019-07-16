import time

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    Blueprint,
    flash,
    abort,
)

from sqlalchemy import desc
from models.base_model import db
from models.board import Board
from routes import (current_user,
                    csrf_required,
                    new_csrf_token,
                    login_required,
                    inform_at,
                    topic_owner_required_post,
                    at_users,
                    cached_topic_id2topic,
                    )

from models.topic import Topic
from routes.myredis import (data_cache,
                            cached_replies_by_topic_id,
                            cached_user_id2user,
                            )

main = Blueprint('my_topic', __name__)


@main.app_template_filter()
def get_author(topic):
    """获取话题作者"""
    author_id = topic.user_id
    return cached_user_id2user(author_id)


@main.app_template_filter()
def content_with_clickable_name(content: str):
    """@功能"""
    for n in at_users(content):
        s = '@' + n.username
        content = content.replace(s, '<a href="/user/{}">@{}</a>'.format(n.id, n.username))
    return content


@main.route('/')
def index():
    """获取话题主页，每个话题cell 最后回复人的头像，
    最后变动时间，作者头像，评论数、浏览数。
    根据query选定板块"""
    visitor = current_user()
    board_id = int(request.args.get('board_id', -1))
    current_bid = board_id
    if board_id == -1:
        recent_active_topics = db.session.query(Topic).order_by(desc(Topic.last_active_time))
    else:
        recent_active_topics = db.session.query(Topic).filter_by(board_id=current_bid).order_by(
            desc(Topic.last_active_time))
    bs = Board.all()
    return render_template('topic/index.html',
                           recent_topics=recent_active_topics,
                           current_bid=current_bid,
                           user=visitor,
                           bs=bs,
                           )


@main.route('/<topic_id>')
def detail(topic_id):
    """
    id 为Topic 的话题的详情页
    """
    cur_topic = Topic.get(topic_id)
    if cur_topic is None:
        return abort(404)

    key = 'topic_id_{}.topic_info'.format(topic_id)
    # 每次有人点开详情页，需要更新浏览数，故旧缓存作废
    data_cache.delete(key)
    replies = cached_replies_by_topic_id(topic_id)
    board = Board.one(id=cur_topic.board_id)
    author = cached_user_id2user(cur_topic.user_id)
    token = new_csrf_token()
    return render_template('topic/detail.html',
                           topic=cur_topic,
                           replies=replies,
                           author=author,
                           token=token,
                           board=board,
                           visitor=current_user()
                           )


@main.route('', methods=['POST'])
@login_required
@csrf_required
def add():
    """
    执行新增Topic
    """
    form = request.form.to_dict()
    u = current_user()
    t = Topic.add(form, user_id=u.id)

    # 新增话题后，user_id 下所有话题的缓存失效，清理旧缓存。
    key = 'user_id_{}.created_topics'.format(u.id)
    data_cache.delete(key)

    inform_at(t, t.content, u)
    return redirect(url_for('.detail', topic_id=t.id))


@main.route("/posting")
@login_required
def new():
    """进入新建Topic的编辑页面"""
    current_bid = int(request.args.get('board_id', -1))
    token = new_csrf_token()
    u = current_user()
    bs = Board.all()
    return render_template("topic/new.html",
                           token=token,
                           user=u,
                           current_bid=current_bid,
                           bs=bs
                           )


@main.route("/deletion", methods=['POST'])
@topic_owner_required_post
@csrf_required
def delete():
    """删除某个话题，话题id从form中获取"""
    user_id = current_user().id
    i = int(request.form.get('topic_id', -1))
    topic = Topic.one(id=i)
    if topic is not None:
        # 删帖后，清理该帖子相关的缓存
        with data_cache.pipeline(transaction=False) as pipe:
            key = 'topic_id_{}.topic_info'.format(i)
            key2 = 'user_id_{}.created_topics'.format(user_id)
            key3 = 'topic_id_{}.replies'.format(topic.id)
            pipe.delete(key)
            pipe.delete(key2)
            pipe.delete(key3)

            delete_rep_id_list = Topic.delete(topic)
            for i in delete_rep_id_list:
                key = 'reply_id_{}.reply_info'.format(i)
                data_cache.delete(key)
            pipe.execute()

        flash('帖子删除成功')
    return redirect(url_for('my_user.user_created_topics', user_id=user_id))


@main.route("/<topic_id>/edit")
@login_required
def edit(topic_id):
    """进入话题编辑页面的get请求"""
    # old_topic: Topic = Topic.one(id=id)
    old_topic: Topic = cached_topic_id2topic(topic_id)
    token = new_csrf_token()
    u = current_user()
    all_borads = Board.all()

    if u.id != old_topic.user_id:
        return abort(404)

    return render_template("topic/edit.html",
                           token=token,
                           user=u,
                           current_bid=old_topic.board_id,
                           bs=all_borads,
                           old_topic=old_topic,
                           )


@main.route("/<int:id>/edit", methods=['POST'])
@login_required
@csrf_required
# 从编辑页面提交修改的post请求
def edit_post(id):
    form = request.form.to_dict()
    now = time.time()
    Topic.update(id, **form, last_edit_time=now, last_active_time=now)
    key = 'topic_id_{}.topic_info'.format(id)
    data_cache.delete(key)
    return redirect(url_for('.detail', topic_id=id))
