from pymongo import MongoClient

def get_users_collection():
    client = MongoClient('mongodb://backontrack:1234567890aA@ds149481.mlab.com:49481/backontrack')
    db = client.backontrack
    collection = db.all_users
    return collection