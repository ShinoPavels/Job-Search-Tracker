from scraper import JobScraper
from database import Database
from ui import JobApp
import tkinter as tk

def main():
    root = tk.Tk()
    app = JobApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()