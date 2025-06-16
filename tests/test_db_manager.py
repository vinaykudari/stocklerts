import os
import tempfile
from datetime import datetime, timedelta, date

from app.database.db_manager import DBManager, User


def create_temp_db():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    url = f"sqlite:///{path}"
    return DBManager(db_url=url), path


def test_reset_daily_counters_resets_with_datetime_date():
    db, path = create_temp_db()
    try:
        with db.Session() as session:
            user = User(notification_count=5, last_notification_date=datetime.now() - timedelta(days=1))
            session.add(user)
            session.commit()

        db.reset_daily_counters()

        with db.Session() as session:
            user_from_db = session.query(User).first()
            assert user_from_db.notification_count == 0
            assert user_from_db.last_notification_date.date() == date.today()
    finally:
        os.remove(path)


def test_reset_daily_counters_same_day_no_reset():
    db, path = create_temp_db()
    try:
        with db.Session() as session:
            user = User(notification_count=5, last_notification_date=datetime.now())
            session.add(user)
            session.commit()

        db.reset_daily_counters()

        with db.Session() as session:
            user_from_db = session.query(User).first()
            assert user_from_db.notification_count == 5
            assert user_from_db.last_notification_date.date() == date.today()
    finally:
        os.remove(path)
