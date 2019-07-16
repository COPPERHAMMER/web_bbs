import time
import uuid


class ServerSession:

    def __init__(self, form):
        self.session_id = form.get('session_id', '')
        self.user_id = form.get('user_id', -1)
        self.expired_time = form.get('expired_time', time.time() + 3600)

    def expired(self):
        now = time.time()
        return self.expired_time < now

    @classmethod
    def new(cls, user_id):
        session_id = str(uuid.uuid4())
        form = dict(
            session_id=session_id,
            user_id=user_id,
        )
        return cls(form)

    def todict(self):
        return self.__dict__
