import time

from sqlalchemy import String, Integer, Column, Text, UnicodeText, Unicode

from models import Model
from models.base_model import SQLMixin, db
from models.user import User
from models.reply import Reply


class Topic(SQLMixin, db.Model):
    views = Column(Integer, nullable=False, default=0)
    title = Column(Unicode(50), nullable=False)
    content = Column(UnicodeText, nullable=False)
    user_id = Column(Integer, nullable=False)
    last_active_time = Column(Integer, nullable=False, default=time.time)
    last_edit_time = Column(Integer, nullable=False, default=time.time)
    board_id = Column(Integer, nullable=False)
    reps = Column(Integer, nullable=False, default=0)
    last_rep_ = Column(Integer, nullable=False, default=-1)

    @classmethod
    def add(cls, form, user_id):
        form['user_id'] = user_id
        m = super().new(form)
        return m

    @classmethod
    def get(cls, id):
        m = cls.one(id=id)
        if m is not None:
            m.views += 1
            m.save()
            return m

    def last_reply(self):
        r = Reply.newest_n(1, topic_id=self.id)
        for rep in r:
            return rep

    @classmethod
    def delete(cls, t):
        replies = Reply.all(topic_id=t.id)
        deleted_rep_id_list = []
        for r in replies:
            r_id = r.id
            db.session.delete(r)
            deleted_rep_id_list.append(r_id)

        db.session.delete(t)
        db.session.commit()
        return deleted_rep_id_list
