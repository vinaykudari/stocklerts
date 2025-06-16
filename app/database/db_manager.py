import datetime

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from datetime import date
from sqlalchemy.orm import scoped_session


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    notification_count = Column(Integer, default=0)
    last_notification_date = Column(DateTime, nullable=True)

    def reset_daily_count(self):
        last_date = None
        if self.last_notification_date:
            if isinstance(self.last_notification_date, datetime.datetime):
                last_date = self.last_notification_date.date()
            else:
                last_date = self.last_notification_date

        if not last_date or last_date < date.today():
            self.notification_count = 0
            self.last_notification_date = date.today()

    def __repr__(self):
        return f"<User(name='{self.id}')>"


class TickerState(Base):
    __tablename__ = 'ticker_states'
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    ticker = Column(String, nullable=False)
    alerted = Column(Boolean, default=False)
    last_alert_thresh = Column(Float, nullable=True)


class DBManager:
    def __init__(self, db_url='sqlite:///stockalerts.db'):
        self.engine = create_engine(db_url, connect_args={'check_same_thread': False})
        Base.metadata.create_all(self.engine)
        self.Session = scoped_session(sessionmaker(bind=self.engine))

    def get_user_notification_count(self, user_id: str):
        with self.Session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                user = User()
                session.add(user)
                session.commit()
            return user.notification_count

    def increment_notification_count(self, user_id: str):
        with self.Session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                user.notification_count += 1
                session.commit()

    def get_ticker_state(self, user_id: str, ticker: str):
        with self.Session() as session:
            state = session.query(TickerState).filter_by(user_id=user_id, ticker=ticker).first()
            if not state:
                state = TickerState(user_id=user_id, ticker=ticker)
                session.add(state)
                session.commit()
            return state.alerted, state.last_alert_thresh

    def set_ticker_alerted(self, user_id: str, ticker: str, thresh: float):
        session = self.Session()
        state = session.query(TickerState).filter_by(user_id=user_id, ticker=ticker).first()
        state.alerted = True
        state.last_alert_thresh = thresh
        session.commit()
        session.close()

    def reset_ticker_alerted(self, user_id: str, ticker: str):
        session = self.Session()
        state = session.query(TickerState).filter_by(user_id=user_id, ticker=ticker).first()
        state.alerted = False
        state.last_alert_thresh = None
        session.commit()
        session.close()

    def reset_daily_counters(self):
        session = self.Session()
        users = session.query(User).all()
        for user in users:
            user.reset_daily_count()
            session.commit()
        session.close()
