import tkinter as tk
import GUIModule
import DBModule
import os

# --- OPTIMIZATION NOTE ---
# The main change is ensuring the database is initialized on first run.
# The DBModule.InitializeDatabase() function will create the SQLite database
# and its tables if they don't already exist.

if __name__ == "__main__":
    # Ensure the database exists before launching the GUI
    DBModule.InitializeDatabase()

    # Create the tkinter parent class
    root = tk.Tk()

    # Load up the interface from the GUIModule
    # The application now manages its own DB connection.
    app = GUIModule.MainApplication(root, bg='navy')
    app.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    # Loop the form so it stays open
    root.mainloop()