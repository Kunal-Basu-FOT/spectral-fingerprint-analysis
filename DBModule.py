import sqlite3
import os
from collections import Counter, deque
import numpy
import json

DB_PATH = os.path.join(os.getcwd(), "music_database.db")

def InitializeDatabase():
    """Create the database tables if they don't exist."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # --- MODIFICATION ---
        # Added the 'filepath' column to store the location of the processed MP3.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                artist TEXT,
                album TEXT,
                year TEXT,
                filepath TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fingerprints (
                hash INTEGER NOT NULL,
                song_id INTEGER NOT NULL,
                offset INTEGER NOT NULL,
                FOREIGN KEY(song_id) REFERENCES songs(id)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_hash ON fingerprints (hash)')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        conn.commit()

def AddSong(metadata):
    """Adds a new song to the songs table and returns its ID."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # --- MODIFICATION ---
        # The INSERT statement now includes the filepath.
        cursor.execute(
            "INSERT INTO songs (title, artist, album, year, filepath) VALUES (?, ?, ?, ?, ?)",
            (metadata['title'], metadata['artist'], metadata['album'], metadata['year'], metadata['filepath'])
        )
        conn.commit()
        return cursor.lastrowid

def GenerateHashes(fingerprint):
    """
    Generate hashes from the constellation map (fingerprint).
    """
    target_zone_size = 5
    anchor_offset = 3
    hashes = []

    if len(fingerprint) < target_zone_size + anchor_offset:
        return []

    for i in range(len(fingerprint) - target_zone_size - anchor_offset):
        anchor_time, anchor_freq = fingerprint[i]
        
        target_zone = fingerprint[i + anchor_offset : i + anchor_offset + target_zone_size]

        for point_time, point_freq in target_zone:
            f1 = round(anchor_freq / 10)
            f2 = round(point_freq / 10)
            dt = round((point_time - anchor_time) * 1000)
            
            hash_val = (f1 << 23) | (f2 << 14) | (dt & 0x3FFF)
            hashes.append((hash_val, round(anchor_time * 1000)))
            
    return hashes

def AddFingerprints(song_id, hashes):
    """Bulk-inserts fingerprint hashes into the database."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        data_to_insert = [(h[0], song_id, h[1]) for h in hashes]
        cursor.executemany(
            "INSERT INTO fingerprints (hash, song_id, offset) VALUES (?, ?, ?)",
            data_to_insert
        )
        conn.commit()

def SearchDatabase(seconds_recorded, fingerprint):
    """
    Searches the database for a matching song.
    """
    if fingerprint.size == 0:
        return 0

    query_hashes = GenerateHashes(fingerprint)
    if not query_hashes:
        return 0

    hash_values = [h[0] for h in query_hashes]
    query_offsets = {h[0]: h[1] for h in query_hashes}

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(hash_values))
        sql_query = f"SELECT song_id, offset, hash FROM fingerprints WHERE hash IN ({placeholders})"
        cursor.execute(sql_query, hash_values)
        db_matches = cursor.fetchall()

    if not db_matches:
        return 0

    time_deltas = {}
    for song_id, db_offset, h in db_matches:
        query_offset = query_offsets.get(h)
        if query_offset is not None:
            delta = db_offset - query_offset
            if song_id not in time_deltas:
                time_deltas[song_id] = []
            time_deltas[song_id].append(delta)

    best_match_id = 0
    max_score = 0
    
    for song_id, deltas in time_deltas.items():
        if not deltas:
            continue
        most_common_delta, score = Counter(deltas).most_common(1)[0]
        
        if score > max_score:
            max_score = score
            best_match_id = song_id
    
    # This threshold might need tuning for short clips
    if max_score < 5:
        return 0
        
    return GetSongById(best_match_id)

def GetSongById(song_id):
    """Retrieves song metadata by its ID."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM songs WHERE id = ?", (song_id,))
        result = cursor.fetchone()
        return dict(result) if result else None

def GetLastMatches(limit=10):
    """Gets the list of last matched songs from the database."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM app_state WHERE key = 'last_matches'")
        result = cursor.fetchone()
        if result:
            return json.loads(result[0])
        return []

def SetLastMatches(matches):
    """Saves the list of last matched songs to the database."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        json_matches = json.dumps(matches)
        cursor.execute(
            "INSERT OR REPLACE INTO app_state (key, value) VALUES ('last_matches', ?)",
            (json_matches,)
        )
        conn.commit()
