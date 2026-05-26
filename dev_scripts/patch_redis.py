with open('db.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("import redis\n_redis = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)\n_redis.ping()", "")
with open('db.py', 'w', encoding='utf-8') as f:
    f.write(text)
