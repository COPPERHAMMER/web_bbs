from sqlalchemy import Column, Unicode, UnicodeText, Integer, Boolean

from models.base_model import SQLMixin, db


class Info(SQLMixin, db.Model):
    title = Column(Unicode(50), nullable=False)
    content = Column(UnicodeText, nullable=False)
    receiver_id = Column(Integer, nullable=False)
    been_read = Column(Boolean, nullable=False, default=False)

    @staticmethod
    def send(title: str, content: str, receiver_id: int):
        form = dict(
            title=title,
            content=content,
            receiver_id=receiver_id,
        )
        Info.new(form)