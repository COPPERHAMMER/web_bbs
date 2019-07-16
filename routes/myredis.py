import json

import redis

from models.info import Info
from models.message import Messages
from models.reply import Reply
from models.topic import Topic
from models.user import User
from utils import log

user_identify_cache = redis.StrictRedis(db=0)
data_cache = redis.StrictRedis(db=1)


def cached_user_id2user(user_id):
    """
    根据user id 返回 User 对象。
    如果缓存命中，则从缓存中拉取包含topic信息的字典，使用get_model得到topic对象。
    如果缓存穿透，则从数据库查询，拿到数据后将数据序列化后存储到redis。
    """
    key = 'user_id_{}.user_info'.format(user_id)
    try:
        # 拿到json 格式的数据
        v = data_cache[key]
    except KeyError:
        # 如果没有缓存
        user = User.one(id=user_id)
        v = json.dumps(user.json())
        data_cache.set(key, v)
        log('缓存丢失，向数据库拉取数据，重建缓存')
        return user
    else:
        # json序列化为dict，dict生成User对象
        d = json.loads(v)
        user = User.get_model(d)
        log('缓存命中，直接使用')

        return user


def cached_topic_id2topic(topic_id):
    """
    根据topic_id 返回对应的Topic 对象。
    如果缓存命中，则从缓存中拉取包含Topic信息的字典，使用get_model得到Topic对象。
    如果缓存穿透，则从数据库查询，拿到数据后将数据序列化后存储到redis。
    """
    key = 'topic_id_{}.topic_info'.format(topic_id)
    try:
        # 缓存命中
        v = data_cache[key]
    except KeyError:
        # 缓存未命中，数据库中拉取数据
        topic = Topic.one(id=topic_id)
        v = json.dumps(topic.json())
        # 加到redis缓存中的是topic id
        data_cache.set(key, v, 300)
        log('缓存丢失，向数据库拉取数据，重建缓存')
        return topic
    else:
        # json序列化为dict，dict生成Topic对象
        d = json.loads(v)
        topic = Topic.get_model(d)
        log('缓存命中，直接使用')
        return topic


def cached_reply_id2reply(reply_id):
    """
    根据reply id 返回 Reply 对象。
    如果缓存命中，则从缓存中拉取包含Reply 信息的字典，使用get_model得到Reply 对象。
    如果缓存穿透，则从数据库查询，拿到数据后将数据序列化后存储到redis。
    """
    key = 'reply_id_{}.reply_info'.format(reply_id)
    try:
        # 拿到json 格式的数据
        v = data_cache[key]
    except KeyError:
        # 如果没有缓存
        reply = Reply.one(id=reply_id)
        v = json.dumps(reply.json())
        data_cache.set(key, v, 3600)
        log('缓存丢失，向数据库拉取数据，重建缓存')
        return reply
    else:
        # json序列化为dict，dict生成Reply对象
        d = json.loads(v)
        reply = Reply.get_model(d)
        log('缓存命中，直接使用')
        return reply


def cached_info_id2info(info_id):
    """
    根据Info id 返回 Info 对象。
    如果缓存命中，则从缓存中拉取包含Info信息的字典，使用get_model得到Info对象。
    如果缓存穿透，则从数据库查询，拿到数据后将数据序列化后存储到redis。
    """
    key = 'info_id_{}.info'.format(info_id)
    try:
        # 拿到json 格式的数据
        v = data_cache[key]
    except KeyError:
        # 如果没有缓存
        info = Info.one(id=info_id)
        v = json.dumps(info.json())
        data_cache.set(key, v, 3600)
        log('缓存丢失，向数据库拉取数据，重建缓存')
        return info
    else:
        # json序列化为dict，dict生成Info对象
        d = json.loads(v)
        info = Info.get_model(d)
        log('缓存命中，直接使用')
        return info


def cached_message_id2message(message_id):
    """
    根据Message id 返回 Message 对象。
    如果缓存命中，则从缓存中拉取包含 Message 信息的字典，使用get_model得到Message对象。
    如果缓存穿透，则从数据库查询，拿到数据后将数据序列化后存储到redis。
    """
    key = 'message_id_{}.message'.format(message_id)
    try:
        # 拿到json 格式的数据
        v = data_cache[key]
    except KeyError:
        # 如果没有缓存
        message = Messages.one(id=message_id)
        v = json.dumps(message.json())
        data_cache.set(key, v)
        log('缓存miss，向数据库拉取数据，重建缓存')
        return message
    else:
        # json序列化为dict，dict生成Info对象
        d = json.loads(v)
        message = Messages.get_model(d)
        log('缓存命中，直接使用')
        return message


def cached_created_topics(user_id):
    """
    根据user id 返回该用户创建的Topic对象。

    如果缓存命中，则从缓存中拉取包含多个Topic id的列表，根据每个Topic id调用cached_topic_id2topic得到Topic对象。
    如果缓存穿透，则从数据库查询，拿到多个Topic对象，将所有Topic id 序列化后存储到redis，返回多个Topic对象。
    """
    key = 'user_id_{}.created_topics'.format(user_id)
    try:
        # 缓存命中
        topic_ids_json = data_cache[key]
    except KeyError:
        # 缓存未命中，数据库中拉取数据
        topics_models = list(Topic.all(user_id=user_id))
        topics_models.sort(key=lambda x: x.last_active_time, reverse=True)
        # 加到redis缓存中的是topic id
        data_cache.set(key, json.dumps([t.id for t in topics_models]), 3600)
        log('缓存丢失，向数据库拉取数据，重建缓存')
        return topics_models
    else:
        # 从缓存中拿到多个Topic id，每个Topic id使用 cached_topic_id2topic获得Topic 对象并返回。
        topics_models = [cached_topic_id2topic(topic_id) for topic_id in json.loads(topic_ids_json)]
        topics_models.sort(key=lambda x: x.last_active_time, reverse=True)
        log('缓存命中，直接使用')
        return topics_models


def cached_replied_topics(user_id):
    """
    根据user id 返回该用户回复的Topic对象。

    如果缓存命中，从缓存中拉取包含多个Topic id的列表，根据每个Topic id调用cached_topic_id2topic得到Topic model。
    如果缓存穿透，则从数据库查询，拿到多个Topic对象，将所有Topic id 序列化后存储到redis，返回多个Topic对象。
    """
    key = 'user_id_{}.replied_topics'.format(user_id)
    try:
        # 缓存命中
        topics_ids_json = data_cache[key]
    except KeyError:
        # 缓存未命中，数据库中拉取数据
        # ORM 的n+1老问题。。。
        replies = list(Reply.all(user_id=user_id))
        topics_ids = [reply.topic_id for reply in replies]
        # 加到redis缓存中的是topic id
        data_cache.set(key, json.dumps(topics_ids), 1800)
        topics_models = [cached_topic_id2topic(topic_id) for topic_id in topics_ids]
        topics_models.sort(key=lambda x: x.last_active_time, reverse=True)
        log('缓存丢失，向数据库拉取数据，重建缓存')
        return topics_models
    else:
        # 缓存命中则根据缓存中的多个Topic id，再调用 cached_topic_id2topic 获得多个Topic对象，排序后返回。
        topics_models = [cached_topic_id2topic(topic_id) for topic_id in json.loads(topics_ids_json)]
        topics_models.sort(key=lambda x: x.last_active_time, reverse=True)
        log('缓存命中，直接使用')
        return topics_models


def cached_replies_by_topic_id(topic_id):
    """
    根据Topic id ,返回属于该Topic的所有Reply对象。

    如果缓存命中，从缓存中拿到包含了多个字典的列表，每个字典都生成一个对应的Reply对象。
    如果缓存穿透，从数据库中查询，拿到多个Reply对象，将每个Reply经json序列化后建立缓存。
    """
    key = 'topic_id_{}.replies'.format(topic_id)
    try:
        # 缓存命中
        replies_json = data_cache[key]
    except KeyError:
        # 缓存未命中，数据库中拉取数据
        replies = list(Reply.all(topic_id=topic_id))
        replies.sort(key=lambda x: x.created_time)
        # 数据库中拿到的数据json序列化后建立缓存，一个Reply对应一个字典
        data_cache.set(key, json.dumps([r.json() for r in replies]), 900)
        log('缓存丢失，向数据库拉取数据，重建缓存')
        return replies
    else:
        # 反序列化后得到字典，使用字典生成Reply对象
        replies = [Reply.get_model(r) for r in json.loads(replies_json)]
        replies.sort(key=lambda x: x.created_time)
        log('缓存命中，直接使用')
        return replies


def cached_received_info(user_id):
    """缓存该用户收到的所有系统消息的id"""
    key = 'user_id_{}.received_info'.format(user_id)
    try:
        # 缓存命中
        info_ids_json = data_cache[key]
    except KeyError:
        # 缓存未命中，数据库中拉取数据model
        info_models = list(Info.all(receiver_id=user_id))
        info_models.sort(key=lambda x: x.created_time, reverse=True)
        # 加到redis缓存中的是id
        data_cache.set(key, json.dumps([i.id for i in info_models]), 3600)
        log('缓存丢失，向数据库拉取数据，重建缓存')
        return info_models
    else:
        # 从缓存中拿到多个Info id
        info_models = [cached_info_id2info(info_id) for info_id in json.loads(info_ids_json)]
        log('缓存命中，直接使用')
        return info_models


def cached_received_message(user_id):
    """缓存该用户收到的所有私信的id"""
    key = 'user_id_{}.received_message'.format(user_id)
    try:
        # 缓存命中
        message_ids_json = data_cache[key]
    except KeyError:
        # 缓存未命中，数据库中拉取数据model
        message_models = list(Messages.all(receiver_id=user_id))
        message_models.sort(key=lambda x: x.created_time, reverse=True)
        # 加到redis缓存中的是id
        data_cache.set(key, json.dumps([m.id for m in message_models]), 3600)
        log('缓存丢失，向数据库拉取数据，重建缓存')
        return message_models
    else:
        # 从缓存中拿到多个Message id
        message_models = [cached_message_id2message(message_id) for message_id in json.loads(message_ids_json)]
        log('缓存命中，直接使用')
        return message_models


def cached_sent_message(user_id):
    """缓存该用户发出的所有私信的id"""
    key = 'user_id_{}.sent_message'.format(user_id)
    try:
        # 缓存命中
        message_ids_json = data_cache[key]
    except KeyError:
        # 缓存未命中，数据库中拉取数据model
        message_models = list(Messages.all(sender_id=user_id))
        message_models.sort(key=lambda x: x.created_time, reverse=True)
        # 加到redis缓存中的是id
        data_cache.set(key, json.dumps([m.id for m in message_models]), 3600)
        log('缓存丢失，向数据库拉取数据，重建缓存')
        return message_models
    else:
        # 从缓存中拿到多个Message id
        message_models = [cached_message_id2message(message_id) for message_id in json.loads(message_ids_json)]
        log('缓存命中，直接使用')
        return message_models
