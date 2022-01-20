
import sys
import path

project_dir = path.Path(__file__).abspath().parent.parent
sys.path.append(project_dir)

from entities import Artist, Track
from config import DATABASE_URL
from sqlalchemy import create_engine

# Create engine for database connection
engine = create_engine(DATABASE_URL, echo=True)

Artist.metadata.create_all(engine)
Track.metadata.create_all(engine)
