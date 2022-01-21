from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Integer, String, Column, ForeignKey

Base = declarative_base()

class Artist(Base):
    __tablename__ = "artists"

    id = Column(Integer, primary_key = True)
    anasheed_id = Column(Integer, unique = True, nullable = False)
    # Searching will be done via this column
    name = Column(String(50), index=True, unique = True, nullable = False)
    image = Column(String(255), nullable = False)

    def save(self, session):
        id = self.__artist_exists(session)
        if not id:
            session.add(self)
            session.commit()
            return self.id
        else:
            return id

    def __artist_exists(self, session):
        artist = session.query(Artist).filter(Artist.anasheed_id == self.anasheed_id).all()
        if artist == []:
            return False
        else:
            # Return the artist_id and use for the consequent operations
            return artist.id

    def __repr__(self):
        return "<Artist(id=%d, name=%s)>" %(self.id, self.name)

class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key = True)
    anasheed_id = Column(Integer, unique = True, nullable = False)
    # Restrict deletion of an artist if he still has tracks in the tracks table
    artist_id = Column(Integer, ForeignKey("artists.id", ondelete="RESTRICT"), nullable = False)
    # Searching will be done via this column
    name = Column(String(100), unique = True, index = True, nullable = False)
    listeners = Column(Integer, default = 0)
    downloads = Column(Integer, default = 0)
    filename = Column(String(255), unique = True, nullable = False)

    def save(self, session):
        id = self.__track_exists(session)
        # If the id is false then commit the transaction and return the assigned primary key
        if not id:
            session.add(self)
            session.commit()
            return self.id
        else:
            return id

    def __track_exists(self, session):
        track = session.query(Track).filter(Track.anasheed_id == self.anasheed_id).all()
        if track == []:
            return False
        else:
            # Return the artist_id and use for the consequent operations
            return track.id

    def __repr__(self):
        return "<Track(id=%d, name=%s)>" %(self.id, self.name)

class Stream(Base):
    __tablename__= "streams"
    id = Column(Integer, primary_key = True)
    reference = Column(String(300), unique = True, nullable = False)
    # Once the track is deleted, delete the reference too
    track_id = Column(Integer, ForeignKey("tracks.id", ondelete="CASCADE"), unique = True, nullable=False)

    def save(self, session):
        id = self.__stream_exists(session)
        # If the id is false then commit the transaction and return the assigned primary key
        if not id:
            session.add(self)
            session.commit()

    def __stream_exists(self, session):
        stream = session.query(Stream).filter(Stream.track_id == self.track_id).all()
        if stream == []:
            return False
        return True
