import os
import glob
from pydub import AudioSegment
from mutagen.mp3 import MP3
import AudioModule
import DBModule
import sqlite3

def extract_metadata(mp3_path):
    """Extracts metadata from an MP3 file."""
    try:
        audio = MP3(mp3_path)
        title = str(audio.get('TIT2', ['Unknown Title'])[0])
        artist = str(audio.get('TPE1', ['Unknown Artist'])[0])
        album = str(audio.get('TALB', ['Single'])[0])
        year_tag = audio.get('TDRC') or audio.get('TYER') or audio.get('TDAT')
        year = str(year_tag[0])[:4] if year_tag else 'Unknown'
        return {'title': title, 'artist': artist, 'album': album, 'year': year}
    except Exception as e:
        print(f"⚠️  Could not extract metadata from {os.path.basename(mp3_path)}: {e}")
        filename = os.path.splitext(os.path.basename(mp3_path))[0]
        return {'title': filename, 'artist': 'Unknown Artist', 'album': 'Single', 'year': 'Unknown'}

def convert_mp3_to_wav(mp3_path, wav_path):
    """Converts MP3 to a temporary WAV file for processing."""
    try:
        audio = AudioSegment.from_mp3(mp3_path)
        audio = audio.set_frame_rate(44100).set_channels(1)
        audio.export(wav_path, format="wav")
        return True
    except Exception as e:
        print(f"❌ Error converting {os.path.basename(mp3_path)}: {e}")
        return False

def add_song_to_database(wav_path, metadata):
    """
    Processes a WAV file and adds the song and its fingerprints to the database.
    """
    try:
        print(f"🎵 Processing: {metadata['title']} by {metadata['artist']}")
        
        fingerprint, _ = AudioModule.GenerateConstellationMap(wav_path)
        if fingerprint.size == 0:
            print("⚠️  Fingerprint generation failed. Skipping.")
            return False

        # The metadata dictionary now includes the filepath
        song_id = DBModule.AddSong(metadata)
        
        hashes = DBModule.GenerateHashes(fingerprint)
        
        DBModule.AddFingerprints(song_id, hashes)
        
        print(f"✅ Added successfully! (Song ID: {song_id})")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error for {metadata['title']}: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error adding {metadata['title']}: {e}")
        return False

def batch_process_songs(songs_folder="Songs", keep_wav_files=False, processed_folder="Processed"):
    """Batch process all MP3 files in a folder."""
    DBModule.InitializeDatabase()

    songs_path = os.path.join(os.getcwd(), songs_folder)
    if not os.path.exists(songs_path):
        os.makedirs(songs_path)
        print(f"Songs folder '{songs_folder}' not found. I've created it for you.")
        print("Please add some .mp3 files to it and run this script again.")
        return

    processed_path = os.path.join(os.getcwd(), processed_folder)
    if not os.path.exists(processed_path):
        os.makedirs(processed_path)
    
    mp3_files = glob.glob(os.path.join(songs_path, "*.mp3"))
    if not mp3_files:
        print(f"❌ No MP3 files found in '{songs_folder}' folder!")
        return
    
    print(f"🎼 Found {len(mp3_files)} MP3 files to process.")
    print("=" * 50)
    
    successful, failed = 0, 0
    temp_wav_dir = os.path.join(os.getcwd(), "temp_wavs")
    if not os.path.exists(temp_wav_dir):
        os.makedirs(temp_wav_dir)

    for i, mp3_path in enumerate(mp3_files, 1):
        filename = os.path.basename(mp3_path)
        wav_path = os.path.join(temp_wav_dir, os.path.splitext(filename)[0] + ".wav")
        
        print(f"\n[{i}/{len(mp3_files)}] Processing: {filename}")
        
        metadata = extract_metadata(mp3_path)
        
        if not convert_mp3_to_wav(mp3_path, wav_path):
            failed += 1
            continue
        
        # --- MODIFICATION ---
        # After processing, the final path of the MP3 is added to the metadata dict.
        processed_mp3_path = os.path.join(processed_path, filename)
        metadata['filepath'] = processed_mp3_path
        
        if add_song_to_database(wav_path, metadata):
            successful += 1
            try:
                os.rename(mp3_path, processed_mp3_path)
            except Exception as e:
                print(f"⚠️  Could not move processed file: {e}")
        else:
            failed += 1
        
        if not keep_wav_files and os.path.exists(wav_path):
            os.remove(wav_path)
            
    print("\n" + "=" * 50)
    print("🎉 BATCH PROCESSING COMPLETE!")
    print(f"✅ Successfully processed: {successful} songs")
    print(f"❌ Failed: {failed} songs")
    
    if os.path.exists(temp_wav_dir) and not os.listdir(temp_wav_dir):
        os.rmdir(temp_wav_dir)

if __name__ == "__main__":
    batch_process_songs()
