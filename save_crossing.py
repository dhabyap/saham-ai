import sys, json, os
sys.path.insert(0, '.')

os.environ['DATABASE_TYPE'] = 'mysql'
os.environ['DB_DRIVER'] = 'mysql'
os.environ['DATABASE_URL'] = 'mysql+mysqlconnector://root:@localhost:3306/analisa_saham'

s = open(r'C:\Users\dhaby\AppData\Local\hermes\cache\documents\doc_7ebe022ba5a2_message.txt', 'r').read()
lines = s.strip().split('\n')
for line in lines:
    if line.startswith('1:'):
        data = json.loads(line[2:])
        break

ticker = data['ticker']
from_dt = data.get('from_date')
to_dt = data.get('to_date')
ca = data.get('crossing_analysis', {})

from app.database.database import get_db
with get_db() as conn:
    conn.execute("""
        INSERT INTO broker_meta (stock_code, period_from, period_to, meta_key, meta_value)
        VALUES (%s, %s, %s, 'crossing_analysis', %s)
        ON DUPLICATE KEY UPDATE meta_value=VALUES(meta_value)
    """, (ticker, from_dt, to_dt, json.dumps(ca)))

    r = conn.execute("SELECT meta_key, JSON_LENGTH(meta_value->'$.potential_crossings') as crosses FROM broker_meta WHERE stock_code='HMSP'").fetchone()
    print(f'Saved: {r[0]} with {r[1]} crossing pairs')
print('Done')
