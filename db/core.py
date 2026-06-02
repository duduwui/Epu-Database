import os
import sys
import logging
import psycopg
from psycopg_pool import ConnectionPool
from config import config
from datetime import date, datetime
import redis as _redis_lib
import json as _json

"""
Database connection and helper functions for MIS System
"""
_pg_bin = r"C:\Program Files\PostgreSQL\17\bin"
if os.path.isdir(_pg_bin) and _pg_bin not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _pg_bin + os.pathsep + os.environ.get("PATH", "")
_conninfo = psycopg.conninfo.make_conninfo(
    host=config.DB_HOST,
    port=int(config.DB_PORT),
    dbname=config.DB_NAME,
    user=config.DB_USER,
    password=config.DB_PASSWORD,
)
_pool = ConnectionPool(conninfo=_conninfo, min_size=2, max_size=20, max_idle=300, open=False)
_redis = None
try:
    _redis = _redis_lib.Redis(host='localhost', port=6379, db=0, decode_responses=True,
        socket_connect_timeout=1, socket_timeout=1, retry_on_timeout=False, retry_on_error=[])
    _redis.ping()
    print("Redis cache: connected")
except Exception:
    _redis = None
    print("Redis cache: not available — running without cache")
CACHE_TTL = 300
CACHE_TTL_LONG = 600
_results_schema_ready = False
_moodle_assignment_schema_ready = False
_teacher_assignment_schema_ready = False
_file_metadata_schema_ready = False
_SUM_GRADE_TYPES = {'midterm'}
_student_engagement_schema_ready = False

def _cache_get(key):
    if _redis is None: return None
    try:
        val = _redis.get(key)
        return _json.loads(val) if val else None
    except Exception: return None

def _cache_set(key, value, ttl=CACHE_TTL):
    if _redis is None or value is None: return
    try: _redis.setex(key, ttl, _json.dumps(value, default=str))
    except Exception: pass

def _cache_delete(*keys):
    if _redis is None: return
    try: _redis.delete(*keys)
    except Exception: pass

def get_db_connection():
    try:
        if _pool.closed:
            _pool.open(wait=False)
        conn = _pool.getconn()
        conn.autocommit = False
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def return_connection(conn):
    try: _pool.putconn(conn)
    except Exception: pass

def row_to_dict(cursor, row):
    if row is None: return None
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))

def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    conn = get_db_connection()
    if not conn: return [] if fetch_all else None
    try:
        cursor = conn.cursor()
        cursor.execute(query, params) if params is not None else cursor.execute(query)
        result = None
        if fetch_one:
            result = row_to_dict(cursor, cursor.fetchone())
            conn.commit()
        elif fetch_all:
            rows = cursor.fetchall()
            result = [row_to_dict(cursor, r) for r in rows] if rows else []
            conn.commit()
        else:
            conn.commit()
            result = cursor.rowcount
        cursor.close()
        return_connection(conn)
        return result
    except Exception as e:
        logging.error("Database query failed", exc_info=True)
        try: conn.rollback()
        except Exception: pass
        return_connection(conn)
        return [] if fetch_all else None

def execute_insert_returning(query, params=None):
    conn = get_db_connection()
    if not conn: return None
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        result = row_to_dict(cursor, row)
        conn.commit()
        cursor.close()
        return_connection(conn)
        return result['id'] if result else None
    except Exception as e:
        logging.error("Database query failed", exc_info=True)
        try: conn.rollback()
        except Exception: pass
        return_connection(conn)
        return None

def _safe_grade_number(value):
    return float(value or 0)

def _summarize_component_rows(rows, force_sum=False):
    items = list(rows or [])
    score_sum = sum(_safe_grade_number(item.get('score')) for item in items)
    max_sum = sum(_safe_grade_number(item.get('max_score')) for item in items)
    count = len(items)

    if force_sum or count <= 1:
        return score_sum, max_sum

    return score_sum / count, max_sum / count

def get_next_pair_group(subject_id):
    """Return the next available pair_group integer for a subject (1-based)."""
    result = execute_query(
        "SELECT COALESCE(MAX(pair_group), 0) + 1 AS next_pg FROM grade_components WHERE subject_id = %s",
        (subject_id,), fetch_one=True
    )
    return int(result['next_pg']) if result else 1

def add_paired_components(subject_id, report_name, seminar_name, weight, display_order=0):
    """Add a paired Report+Seminar pair. Both share the same pair_group so their scores
    are averaged for grade calculation and together consume only `weight`% of the budget."""
    pg = get_next_pair_group(subject_id)
    rid = add_grade_component(subject_id, 'report', report_name, weight, weight, display_order, pair_group=pg)
    sid = add_grade_component(subject_id, 'seminar', seminar_name, weight, weight, display_order + 1, pair_group=pg)
    return rid, sid, pg

def get_component_count_by_type(subject_id, component_type):
    """Get count of existing components of a specific type for auto-numbering"""
    query = """
        SELECT COUNT(*) as count
        FROM grade_components
        WHERE subject_id = %s AND component_type = %s
    """
    result = execute_query(query, (subject_id, component_type), fetch_one=True)
    return int(result['count']) if result else 0

def update_component_display_order(component_id, new_order):
    """Update the display order of a single grade component"""
    query = """
        UPDATE grade_components
        SET display_order = %s
        WHERE id = %s
    """
    try:
        execute_query(query, (new_order, component_id))
        return True
    except Exception as e:
        print(f"Error updating display order: {e}")
        return False

def reorder_categories_by_type(subject_id, category_order_list):
    """
    Reorder all components by category position
    category_order_list: list of component_types in desired order
    Each category gets a base order (0, 100, 200...), components within are sequential
    """
    try:
        print(f"Reordering categories for subject {subject_id}")
        print(f"New order: {category_order_list}")
        
        for idx, component_type in enumerate(category_order_list):
            base_order = idx * 100
            print(f"Processing category {component_type} at position {idx} (base_order={base_order})")
            
            # Get all components of this type, ordered by current display_order
            query_get = """
                SELECT id, component_name, display_order FROM grade_components
                WHERE subject_id = %s AND component_type = %s
                ORDER BY display_order, id
            """
            components = execute_query(query_get, (subject_id, component_type), fetch_all=True)
            print(f"  Found {len(components) if components else 0} components")
            
            if components:
                # Update each component with sequential ordering
                for i, comp in enumerate(components):
                    new_order = base_order + i
                    old_order = comp['display_order']
                    print(f"    Updating {comp['component_name']}: {old_order} -> {new_order}")
                    query_update = """
                        UPDATE grade_components
                        SET display_order = %s
                        WHERE id = %s
                    """
                    result = execute_query(query_update, (new_order, comp['id']))
                    print(f"      Update result: {result}")
        
        print("Reordering complete!")
        return True
    except Exception as e:
        print(f"Error reordering categories: {e}")
        import traceback
        traceback.print_exc()
        return False
