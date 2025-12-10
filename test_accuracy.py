import os
import random
import sqlite3
import time
from pydub import AudioSegment
import numpy as np
import AudioModule
import DBModule

# --- GUI SIMULATION CONFIGURATION ---
TOTAL_CLIP_DURATION_MS = 7000  # Total clip length
CHUNK_DURATION_MS = 1000       # Process in 1-second chunks (like GUI)
TESTS_PER_SONG = 5
TEMP_RECORDING_PATH = "temp_recording.wav"

def get_all_songs_from_db():
    """Fetches all songs with their ID and filepath from the database."""
    with sqlite3.connect(DBModule.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, artist, filepath FROM songs")
        songs = cursor.fetchall()
        return [dict(row) for row in songs]

def simulate_incremental_recording(audio_clip, temp_file_path):
    """
    Simulates the GUI's incremental recording behavior.
    Writes audio chunks progressively and tests recognition after each chunk.
    """
    # Clear any existing temp file
    if os.path.exists(temp_file_path):
        os.remove(temp_file_path)
    
    # Convert to mono 44.1kHz (matching GUI)
    audio_clip = audio_clip.set_channels(1).set_frame_rate(44100)
    
    total_duration = len(audio_clip)
    chunks_needed = min(total_duration // CHUNK_DURATION_MS, TOTAL_CLIP_DURATION_MS // CHUNK_DURATION_MS)
    
    start_search_time = time.time()
    
    for chunk_num in range(1, chunks_needed + 1):
        chunk_end_time = chunk_num * CHUNK_DURATION_MS
        current_audio = audio_clip[:chunk_end_time]
        
        # Write the progressively growing audio file (like GUI does)
        current_audio.export(temp_file_path, format="wav")
        
        # Try to identify (like GUI does after each chunk)
        fingerprint = AudioModule.GenerateConstellationMap(temp_file_path)
        
        if fingerprint.size > 0:
            result = DBModule.SearchDatabase(chunk_end_time/1000, fingerprint)
            if result:
                # Found a match! Return immediately (like GUI)
                search_duration = time.time() - start_search_time
                return result, search_duration, chunk_num
        
        # Small delay to simulate real-time recording (optional)
        time.sleep(0.1)
    
    # No match found even with full clip
    search_duration = time.time() - start_search_time
    return None, search_duration, chunks_needed

def run_gui_simulation_test(songs_to_test):
    """
    Tests the system using GUI-like incremental processing.
    """
    if not songs_to_test:
        print("No songs found in the database to test.")
        return

    print(f"Starting GUI-SIMULATION accuracy test on {len(songs_to_test)} songs...")
    print(f"Processing in {CHUNK_DURATION_MS/1000}s chunks, up to {TOTAL_CLIP_DURATION_MS/1000}s total")
    print("-" * 50)

    song_success_count = 0
    total_clip_tests = 0
    search_times = []
    chunks_to_recognition = []

    for i, song in enumerate(songs_to_test):
        original_song_id = song['id']
        song_path = song['filepath']

        if not song_path or not os.path.exists(song_path):
            print(f"⚠️  Skipping '{song['title']}': Filepath not found or invalid.")
            continue

        try:
            audio = AudioSegment.from_mp3(song_path)
        except Exception as e:
            print(f"❌ Error loading '{song['title']}': {e}")
            continue

        if len(audio) < TOTAL_CLIP_DURATION_MS:
            print(f"ℹ️  Skipping '{song['title']}': Too short to test.")
            continue

        print(f"({i+1}/{len(songs_to_test)}) Testing: {song['title']} by {song['artist']}")
        song_successes = 0

        for test_num in range(TESTS_PER_SONG):
            total_clip_tests += 1

            # Random starting point for clip
            max_start_time = len(audio) - TOTAL_CLIP_DURATION_MS
            start_time = random.randint(0, max_start_time)
            clip = audio[start_time : start_time + TOTAL_CLIP_DURATION_MS]
            
            # Simulate incremental recording and recognition
            result_metadata, search_duration, chunks_used = simulate_incremental_recording(
                clip, TEMP_RECORDING_PATH
            )
            
            search_times.append(search_duration)
            
            if result_metadata and result_metadata['id'] == original_song_id:
                song_successes += 1
                chunks_to_recognition.append(chunks_used)
                recognition_time = chunks_used * (CHUNK_DURATION_MS/1000)
                print(f"  ✅ Test {test_num+1}: Identified after {recognition_time}s of audio (Took {search_duration:.3f}s total)")
            elif result_metadata:
                print(f"  ❌ Test {test_num+1}: Incorrectly identified as '{result_metadata['title']}' (Took {search_duration:.3f}s)")
            else:
                print(f"  ❌ Test {test_num+1}: Could not identify (Took {search_duration:.3f}s)")

        if song_successes == TESTS_PER_SONG:
            song_success_count += 1
            
        print(f"  📊 Song accuracy: {song_successes}/{TESTS_PER_SONG} ({(song_successes/TESTS_PER_SONG)*100:.1f}%)")

    # Clean up
    if os.path.exists(TEMP_RECORDING_PATH):
        os.remove(TEMP_RECORDING_PATH)

    # --- Final Report ---
    print("\n" + "=" * 50)
    print("🎉 GUI-SIMULATION TEST COMPLETE 🎉")
    print("-" * 50)
    
    if total_clip_tests > 0:
        num_songs_tested = len([s for s in songs_to_test if os.path.exists(s.get('filepath', ''))])
        song_accuracy = (song_success_count / num_songs_tested) * 100 if num_songs_tested > 0 else 0
        clip_accuracy = (len([t for t in search_times if 'success' in str(t)]) / total_clip_tests) * 100
        avg_search_time = sum(search_times) / len(search_times) if search_times else 0
        
        print(f"Songs fully identified: {song_success_count} / {num_songs_tested}")
        print(f"Song-level Accuracy: {song_accuracy:.2f}%")
        print(f"Average Processing Time per Clip: {avg_search_time:.3f} seconds")
        
        if chunks_to_recognition:
            avg_chunks = sum(chunks_to_recognition) / len(chunks_to_recognition)
            avg_recognition_time = avg_chunks * (CHUNK_DURATION_MS/1000)
            print(f"Average Audio Needed for Recognition: {avg_recognition_time:.1f} seconds")
            print(f"Fastest recognition: {min(chunks_to_recognition) * (CHUNK_DURATION_MS/1000):.1f}s")
        
        if search_times:
            print(f"Fastest processing: {min(search_times):.3f} seconds")
            print(f"Slowest processing: {max(search_times):.3f} seconds")
    else:
        print("No tests were run.")


if __name__ == "__main__":
    # Ensure the database file exists before running the test
    if not os.path.exists(DBModule.DB_PATH):
        print(f"❌ Database file not found at '{DBModule.DB_PATH}'.")
        print("Please run 'AddSongs.py' first to create and populate the database.")
    else:
        all_songs = get_all_songs_from_db()

        if not all_songs:
            print("❌ Database is empty. Please add songs using 'AddSongs.py' first.")
        else:
            print(f"Found {len(all_songs)} songs in database.")
            
            while True:
                try:
                    num_to_test_str = input(f"How many songs would you like to test? (1-{len(all_songs)}, or 'all'): ")
                    if num_to_test_str.lower() == 'all':
                        num_to_test = len(all_songs)
                        break
                    num_to_test = int(num_to_test_str)
                    if 1 <= num_to_test <= len(all_songs):
                        break
                    else:
                        print(f"Invalid number. Please enter a number between 1 and {len(all_songs)}.")
                except ValueError:
                    print("Invalid input. Please enter a number or 'all'.")

            selected_songs = random.sample(all_songs, num_to_test)
            run_gui_simulation_test(selected_songs)