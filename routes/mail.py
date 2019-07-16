from flask import (
    render_template,
    request,
    redirect,
    url_for,
    Blueprint,
    flash, abort, )

from models.message import Messages
from models.user import User
from routes import (login_required,
                    current_user,
                    cached_user_id2user,
                    new_csrf_token,
                    csrf_required,
                    )
from routes.myredis import (cached_sent_message,
                            data_cache,
                            cached_received_message,)

main = Blueprint('mail', __name__)


@main.app_template_filter()
def get_sender(message):
    """获取某条私信的发件人"""
    sender_id = message.sender_id
    return cached_user_id2user(sender_id)


@main.app_template_filter()
def get_receiver(k):
    """获取某条私信的收件人"""
    receiver_id = k.receiver_id
    return cached_user_id2user(receiver_id)


@main.app_template_global()
def unread_message_num_of_user(u):
    """获取未读私信条数"""
    if u is not None:
        uid = u.id
        all_messages = cached_received_message(uid)
        unread_messages = [m for m in all_messages if not m.been_read]
        n = len(unread_messages)
        if n > 0:
            return '[%d]' % n
    return ''


@main.route('/set_read', methods=['POST'])
@login_required
def set_read():
    """标记所有未读私信为已读"""
    u = current_user()
    receiver_id = int(request.form.get('receiver_id', -1))
    receiver = cached_user_id2user(receiver_id)
    if receiver is not None:
        if receiver_id == u.id:
            unread_messages = Messages.all(receiver_id=receiver_id, been_read=False)

            with data_cache.pipeline(transaction=False) as pipe:
                for message in unread_messages:
                    key = 'message_id_{}.message'.format(message.id)
                    message.been_read = True
                    message.save()
                    pipe.delete(key)
                pipe.execute()

    return redirect(url_for('.inbox'))


@main.route("/deliver", methods=["POST"])
@login_required
@csrf_required
def add():
    """发送新私信"""
    form = request.form.to_dict()
    u = current_user()
    receiver_id = form.get('receiver_id', None)

    if receiver_id is None:
        r_name = form.get('receiver_name', None)
        receiver = User.one(username=r_name)
    else:
        # receiver = User.one(id=receiver_id)
        receiver = cached_user_id2user(receiver_id)
    if receiver is None:
        flash('收件人不存在')
    elif receiver.id == u.id or receiver.username == u.username:
        flash('私信是发给其他人的哦，请重新输入收件人')
    else:
        Messages.send(
            title=form['title'],
            content=form['content'],
            sender_id=u.id,
            receiver_id=receiver.id,
        )
        flash('发送成功')
        with data_cache.pipeline(transaction=False) as pipe:
            key = 'user_id_{}.sent_message'.format(u.id)
            key2 = 'user_id_{}.received_message'.format(receiver_id)
            pipe.delete(key)
            pipe.delete(key2)
            pipe.execute()
    return redirect(url_for('.index'))


@main.route('/')
@login_required
def index():
    u = current_user()
    token = new_csrf_token()

    recv = Messages.newest_n(3, receiver_id=u.id)
    t = render_template(
        'mail/index.html',
        user=u,
        token=token,
        received=recv,
    )
    return t


@main.route('/inbox')
@login_required
def inbox():
    u = current_user()
    # unread = list(Messages.all(receiver_id=u.id, been_read=False))
    # unread.sort(key=lambda x: x.created_time, reverse=True)
    #
    # been_read = list(Messages.all(receiver_id=u.id, been_read=True))
    # been_read.sort(key=lambda x: x.created_time, reverse=True)
    all_messages = cached_received_message(u.id)

    unread = [m for m in all_messages if not m.been_read]
    been_read = [m for m in all_messages if m.been_read]

    return render_template('mail/inbox.html',
                           user=u,
                           unread=unread,
                           been_read=been_read
                           )


@main.route('/sent_box')
def sent_box():
    u = current_user()
    # sent_mails = list(Messages.all(sender_id=u.id))
    sent_mails = cached_sent_message(u.id)
    # sent_mails.sort(key=lambda x: x.created_time, reverse=True)
    return render_template('mail/sent_box.html',
                           user=u,
                           sent=sent_mails,
                           )


@main.route('/<int:id>')
@login_required
def view(id):
    message: Messages = Messages.one(id=id)
    u = current_user()
    is_sender = u.id == message.sender_id
    is_receiver = u.id == message.receiver_id
    if is_receiver or is_sender:

        if is_receiver and not message.been_read:
            message.been_read = True
            message.save()
            key = 'message_id_{}.message'.format(message.id)
            data_cache.delete(key)

        return render_template('mail/detail.html', message=message, user=u)
    else:
        return abort(404)


@main.route('/reply_page')
@login_required
def send_back():
    """用于回复私信"""
    receiver_id = request.args.get('receiver_id')
    token = new_csrf_token()
    u = current_user()
    receiver = cached_user_id2user(receiver_id)
    return render_template('mail/reply_page.html', user=u, token=token, receiver=receiver)
