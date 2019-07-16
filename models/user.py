from flask import flash
from sqlalchemy import Column, String

import config
from models.base_model import SQLMixin, db


class User(SQLMixin, db.Model):
    """
    User 是一个保存用户数据的 model
     用户名 和 用户密码
     用户头像uri 和 用户邮箱
    """
    username = Column(String(50), nullable=False)
    password = Column(String(256), nullable=False)
    image = Column(String(100), nullable=False, default='/images/default_profile.jpg')
    email = Column(String(50), nullable=False, default=config.test_mail)
    signature = Column(String(256), nullable=False, default='该用户太懒,什么也没有写。')

    @classmethod
    def salted_password(cls, password, salt='$!@><?>HUI&DWQa`'):
        import hashlib

        def sha256(ascii_str):
            return hashlib.sha256(ascii_str.encode('ascii')).hexdigest()

        hash1 = sha256(password)
        hash2 = sha256(hash1 + salt)
        print('sha256', len(hash2))
        return hash2

    def hashed_password(self, pwd):
        import hashlib
        # 用 ascii 编码转换成 bytes 对象
        p = pwd.encode('ascii')
        s = hashlib.sha256(p)
        # 返回摘要字符串
        return s.hexdigest()

    @classmethod
    def register(cls, form):
        name = form['username']
        password = form['password']
        email = form['email']
        if User.one(email=email) is not None or User.one(username=name) is not None:
            flash('用户名被占用，请重新输入')
            return None

        if len(name) > 0 and len(password) > 2:
            u = User.new(form)
            u.password = u.salted_password(password)
            u.save()
            return u

    @classmethod
    def validate_login(cls, form):
        user = User.one(username=form['username'])
        if user is not None and user.password == User.salted_password(form['password']):
            return user
        else:
            return None
