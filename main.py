from src.populate_db import PopulateDB
from src.database import Database

if __name__ == "__main__":
    db = Database("main")
    populator = PopulateDB(db)
    populator.populate_all_sources()
    # print(db.get_article(1).get('content'))
