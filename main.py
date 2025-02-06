from src.populate_db import PopulateDB
from src.fetchdatabase import FetchDatabase

if __name__ == "__main__":
    db = FetchDatabase("main")
    populator = PopulateDB(db)
    populator.populate_all_sources()
    # print(db.get_article(1).get('content'))
