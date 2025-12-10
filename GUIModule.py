import tkinter as tk
import time
import threading
import AudioModule
import DBModule
from collections import deque
from timeit import default_timer as timer
import os

class MainApplication(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.parent.geometry("400x600")
        self.parent.title("MusicID")
        self.AddWidgets(True)

    def recordButtonClick(self):
        self.lastSongsButton.place_forget()
        tk.Frame.config(self, bg='red')
        self.recordButton.config(text="Listening")
        self.titleLabel.config(bg='red')
        self.update()

        # The recording thread will now periodically save chunks of audio
        self.recordAudioThread = threading.Thread(target=AudioModule.RecordAudio, args=(15, os.path.join(os.getcwd(), "RecordedAudio.wav"), 1))
        self.recordAudioThread.start()

        self.counterThread = threading.Thread(target=self.CountSeconds)
        self.counterThread.start()
        self.start = timer()
        time.sleep(2) # Initial wait for the first chunk of audio to be saved

        self.identifySongThread = threading.Thread(target=self.IDSong, args=(os.path.join(os.getcwd(), "RecordedAudio.wav"),))
        self.identifySongThread.start()

    def CountSeconds(self):
        self.secondsPassed = 0
        for i in range(1, 11):
            time.sleep(1)
            self.secondsPassed = i

    def AddWidgets(self, firstLaunch):
        if firstLaunch:
            labelFont = ("Helvetica", 40, "bold")
            self.titleLabel = tk.Label(self, text="MusicID", font=labelFont, bg="navy", fg="yellow")
            self.titleLabel.pack(side=tk.TOP)

        buttonFont = ("Helvetica", 20)
        self.recordButton = tk.Button(self, text="Record", height=10, width=20, command=self.recordButtonClick, font=buttonFont, bg="blue")
        self.recordButton.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self.lastSongsButton = tk.Button(self, text='Previous Matches', height=2, width=15, command=self.ShowLastMatches, font=buttonFont)
        self.lastSongsButton.place(relx=0.5, rely=0.9, anchor=tk.CENTER)
        
        self.lastSongsMatched = deque(DBModule.GetLastMatches(10), maxlen=10)

    def AllChildren(self, window):
        _list = window.winfo_children()
        for item in _list:
            if item.winfo_children():
                _list.extend(item.winfo_children())
        return _list

    def ResetWidgets(self):
        # This is a more robust way to clear the widgets
        for widget in self.winfo_children():
            if widget != self.titleLabel:
                widget.destroy()
        self.AddWidgets(False)

    def ShowResults(self, songMetaData, searchTime):
        self.recordButton.place_forget()
        self.lastSongsButton.place_forget()

        songTitleFont = ("Helvetica", 25, 'bold')
        otherFont = ("Helvetica", 16)
        buttonFont = ("Helvetica", 20)

        if not songMetaData:
            self.songTitle = tk.Label(self, text='Song Not Found', font=songTitleFont, bg='navy', fg='green')
        else:
            name, artist, album, releaseDate = songMetaData['title'], songMetaData['artist'], songMetaData['album'], songMetaData['year']
            self.songTitle = tk.Label(self, text=f'Song: {name}', font=songTitleFont, bg='navy', fg='green')
            tk.Label(self, text=f'Artist: {artist}', font=otherFont, bg='navy', fg='yellow').place(relx=0.5, rely=0.32, anchor=tk.CENTER)
            
            album_text = 'Released as a single' if (album == 'Single' or not album) else f'Album: {album}'
            tk.Label(self, text=album_text, font=otherFont, bg='navy', fg='yellow').place(relx=0.5, rely=0.37, anchor=tk.CENTER)
            tk.Label(self, text=f'Release Date: {releaseDate}', font=otherFont, bg='navy', fg='yellow').place(relx=0.5, rely=0.42, anchor=tk.CENTER)
        
        tk.Label(self, text=f'Search Time: {searchTime} seconds', font=otherFont, bg='navy', fg='grey').place(relx=0.5, rely=0.85, anchor=tk.CENTER)
        tk.Button(self, text='Back', font=buttonFont, command=self.ResetWidgets).place(relx=0.5,rely=0.75, anchor=tk.CENTER)

        self.songTitle.place(relx=0.5, rely=0.25, anchor=tk.CENTER)

        if songMetaData:
            match_string = f"{songMetaData['title']} by {songMetaData['artist']}"
            if match_string not in self.lastSongsMatched:
                self.lastSongsMatched.appendleft(match_string)
            DBModule.SetLastMatches(list(self.lastSongsMatched))

    def ShowLastMatches(self):
        self.recordButton.place_forget()
        self.lastSongsButton.place_forget()

        buttonFont = ("Helvetica", 20)
        tk.Button(self, text='Back', font=buttonFont, command=self.ResetWidgets).place(relx=0.5,rely=0.8, anchor=tk.CENTER)

        if self.lastSongsMatched:
            tk.Button(self, text='Clear', font=buttonFont, command=self.ClearPreviousMatches).place(relx=0.5,rely=0.9, anchor=tk.CENTER)
        else:
            tk.Label(self, text='No Previous Matches', font=buttonFont, bg='navy', fg='yellow').place(relx=0.5, rely=0.35, anchor=tk.CENTER)

        labelFont = ("Helvetica", 16)
        yCoords = [0.16 + i * 0.06 for i in range(10)]
        self.arrayOfLabels = []
        for i, match_text in enumerate(self.lastSongsMatched):
            label = tk.Label(self, text=f"{i + 1}. {match_text}", font=labelFont, bg='navy', fg='yellow')
            label.place(relx=0.1, rely=yCoords[i], anchor=tk.W)
            self.arrayOfLabels.append(label)

    def ClearPreviousMatches(self):
        self.lastSongsMatched.clear()
        DBModule.SetLastMatches([])
        self.ResetWidgets()

    def IDSong(self, filepath):
        """
        FIX: This function now loops internally, trying to identify the song
        as the recording grows. It's more robust than the previous recursion.
        """
        self.songMetaData = 0
        while self.recordAudioThread.is_alive() and not self.songMetaData:
            # Generate the fingerprint from the entire file so far.
            # AudioModule is now resilient to file-read errors.
            fingerprint = AudioModule.GenerateConstellationMap(filepath)
            
            # Only search if we have a valid fingerprint
            if fingerprint.size > 0:
                self.songMetaData = DBModule.SearchDatabase(self.secondsPassed, fingerprint)

            # Wait a moment before re-processing the file
            time.sleep(1.0)
        
        # --- Finalization (runs after loop ends) ---
        self.finish = timer() - self.start
        search_time = str(round(self.finish, 3))
        
        # Ensure the UI updates happen on the main thread
        self.parent.after(0, self.FinalizeUI, self.songMetaData, search_time)

    def FinalizeUI(self, songMetaData, search_time):
        """Helper function to ensure UI updates are thread-safe."""
        AudioModule.stopCondition = True
        tk.Frame.config(self, bg='navy')
        self.titleLabel.config(bg='navy')
        self.update()
        self.ShowResults(songMetaData, search_time)
