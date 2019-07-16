from flask import (render_template,
                   request,
                   redirect,
                   url_for,
                   abort,
                   Blueprint,
                   )

from models.info import Info
from routes import (login_required,
                    csrf_required,
                    current_user,
                    new_csrf_token,
                    )

from routes.myredis import (cached_received_info,
                            cached_user_id2user,
                            data_cache,
                            )

main = Blueprint('info', __name__)


@main.app_template_global()
def unread_info_num_of_user(u):
    """用于显示未读信息数"""
    if u is not None:
        uid = u.id
        all_info = cached_received_info(uid)
        unread_info = [i for i in all_info if not i.been_read]
        n = len(unread_info)
        if n > 0:
            return '[%d]' % n
    return ''


@main.route('/')
@login_required
def info():
    """系统通知主页，查看所有系统通知"""
    user = current_user()
    all_info = cached_received_info(user.id)

    unread_info = [i for i in all_info if not i.been_read]
    been_read_info = [i for i in all_info if i.been_read]
    token = new_csrf_token()
    return render_template("info/info.html",
                           user=user,
                           token=token,
                           unread=unread_info,
                           been_read=been_read_info,
                           )


@main.route('/deletion', methods=['POST'])
@login_required
@csrf_required
def delete():
    """执行系统通知的删除操作"""
    u = current_user()
    info_id = int(request.form.get('info_id', -1))
    i: Info = Info.one(id=info_id)
    if i is not None:
        # 权限验证
        if i.receiver_id == u.id:
            Info.delete(i)
            key = 'user_id_{}.received_info'.format(u.id)
            data_cache.delete(key)
            return redirect(url_for('.info'))

    return abort(404)


@main.route('/<info_id>')
@login_required
def detail(info_id):
    """查看系统通知详情"""
    u = current_user()
    i: Info = Info.one(id=info_id)
    if i is None or u.id != i.receiver_id:
        return abort(404)

    if not i.been_read:
        i.been_read = True
        i.save()
        key = 'info_id_{}.info'.format(i.id)
        data_cache.delete(key)

    token = new_csrf_token()
    return render_template("info/info_detail.html", user=u, info=i, token=token)


@main.route('/sweeper', methods=['POST'])
@login_required
@csrf_required
def sweep():
    """清理所有已读信息"""
    u = current_user()
    owner_id = int(request.form.get('owner_id', -1))
    owner = cached_user_id2user(owner_id)
    if owner is not None:
        if owner_id == u.id:
            read_infos = Info.all(receiver_id=owner_id, been_read=True)
            with data_cache.pipeline(transaction=False) as pipe:
                for i in read_infos:
                    Info.delete(i)
                    key = 'user_id_{}.received_info'.format(u.id)
                    pipe.delete(key)
                pipe.execute()

    return redirect(url_for('.info'))


@main.route('/set_read', methods=['POST'])
@login_required
def set_read():
    """一键标记所有信息为已读"""
    u = current_user()
    owner_id = int(request.form.get('owner_id', -1))
    owner = cached_user_id2user(owner_id)
    if owner is not None:
        if owner_id == u.id:
            unread_info = Info.all(receiver_id=owner_id, been_read=False)

            with data_cache.pipeline(transaction=False) as pipe:
                for i in unread_info:
                    i.been_read = True
                    i.save()
                    key = 'info_id_{}.info'.format(i.id)
                    pipe.delete(key)
                pipe.execute()

    return redirect(url_for('.info'))
