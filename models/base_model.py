import time

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, desc

db = SQLAlchemy()


class SQLMixin(object):
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    created_time = Column(Integer, default=time.time)
    updated_time = Column(Integer, default=time.time)

    @classmethod
    def new(cls, form):
        m = cls()
        for name, value in form.items():
            setattr(m, name, value)
        m.save()

        return m

    @classmethod
    def get_model(cls, form):
        m = cls()
        for name, value in form.items():
            setattr(m, name, value)
        return m

    @classmethod
    def update(cls, id, **kwargs):
        # User.update(12, username='gua', password='123')
        # u.username = 'gua'
        # db.session.add(u)
        # db.session.commit()
        m = cls.query.filter_by(id=id).first()
        for name, value in kwargs.items():
            setattr(m, name, value)

        m.save()

    @classmethod
    def all(cls, **kwargs):
        ms = cls.query.filter_by(**kwargs).all()
        return ms

    @classmethod
    def one(cls, **kwargs):
        ms = cls.query.filter_by(**kwargs).first()
        return ms

    @classmethod
    def columns(cls):
        return cls.__mapper__.c.items()

    @classmethod
    def newest_n(cls, n=None, **kwargs):
        if kwargs:
            r = db.session.query(cls).filter_by(**kwargs).order_by(desc(cls.created_time))
        else:
            r = db.session.query(cls).order_by(desc(cls.created_time))
        if n is not None:
            r = r.limit(n)
        return list(r)

    def __repr__(self):
        """
        __repr__ 是一个魔法方法
        简单来说, 它的作用是得到类的 字符串表达 形式
        比如 print(u) 实际上是 print(u.__repr__())
        不明白就看书或者 搜
        """
        name = self.__class__.__name__
        s = ''
        for attr, column in self.columns():
            if hasattr(self, attr):
                v = getattr(self, attr)
                s += '{}: ({})\n'.format(attr, v)
        return '< {}\n{} >\n'.format(name, s)

    def save(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def delete(cls, item):
        db.session.delete(item)
        db.session.commit()

    def json(self):
        d = dict()
        for attr, column in self.columns():
            if hasattr(self, attr):
                v = getattr(self, attr)
                d[attr] = v
        return d

# class SimpleUser(SQLMixin, db.Model):
#     # username: str
#     username = Column(String(50), nullable=False)
#     password = Column(String(50), nullable=False)
#
#     # def __init__(self):
#     #     self.username = form.get('username', 'guest')
#     #     self.password = 'xxx'
#
#
# if __name__ == '__main__':
#     db.create_all()
#     form = dict(
#         username='123',
#         password='456',
#     )
#     u = SimpleUser.new(form)
#     print(u)
#     u = SimpleUser.one(username='123')
#     print(u)
