import os, sys, json
sys.path.insert(0, '.')
os.environ['DATABASE_TYPE'] = 'mysql'
os.environ['DB_DRIVER'] = 'mysql'
os.environ['DATABASE_URL'] = 'mysql+mysqlconnector://root:@localhost:3306/analisa_saham'

from app.database.database import get_db

with get_db() as conn:
    # Test tables
    tables = conn.execute("SHOW TABLES").fetchall()
    table_names = [list(t.values())[0] if hasattr(t, 'values') else t[0] for t in tables]
    print('Tables:', ', '.join(table_names))

    # Check broker_meta
    r = conn.execute("SELECT meta_key, JSON_LENGTH(meta_value->'$.potential_crossings') as cnt FROM broker_meta WHERE stock_code='HMSP'").fetchone()
    if r:
        vals = list(r.values()) if hasattr(r, 'values') else r
        print(f'Found: {vals}')
    else:
        print('No data in broker_meta for HMSP')

    # Check broker_summary
    r = conn.execute("SELECT COUNT(*) FROM broker_summary WHERE stock_code='HMSP'").fetchone()
    cnt = list(r.values())[0] if hasattr(r, 'values') else r[0]
    print(f'broker_summary HMSP entries: {cnt}')
