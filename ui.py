import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import sqlite3
from scraper import JobScraper  # Import JobScraper to run the scraper directly

class JobSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Job Search Tracker")
        
        self.db_path = 'data/jobs.db'  # Path to the database
        self.sort_state = {}  # Dictionary to hold sort state for each column

        # Initialize scraper
        self.scraper = JobScraper()

        # Frame to hold the Treeview and scrollbar
        tree_frame = tk.Frame(root)
        tree_frame.pack(expand=True, fill='both', padx=10, pady=10)

        # Create Treeview widget to display jobs
        self.tree = ttk.Treeview(tree_frame, columns=("ID", "Title", "Location", "Salary", "Advantages", "Description", "Checked"), show='headings')
        
        # Define column headings with a binding for sorting
        self.tree.heading("ID", text="ID", command=lambda: self.sort_column("ID"))
        self.tree.heading("Title", text="Title", command=lambda: self.sort_column("Title"))
        self.tree.heading("Location", text="Location", command=lambda: self.sort_column("Location"))
        self.tree.heading("Salary", text="Salary", command=lambda: self.sort_column("Salary"))
        self.tree.heading("Advantages", text="Advantages", command=lambda: self.sort_column("Advantages"))
        self.tree.heading("Description", text="Description", command=lambda: self.sort_column("Description"))
        self.tree.heading("Checked", text="Checked", command=lambda: self.sort_column("Checked"))

        # Set column width to ensure all text is visible
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Title", width=200, anchor="w")
        self.tree.column("Location", width=150, anchor="w")
        self.tree.column("Salary", width=100, anchor="w")
        self.tree.column("Advantages", width=150, anchor="w")
        self.tree.column("Description", width=300, anchor="w")
        self.tree.column("Checked", width=80, anchor="center")

        # Apply styling to Treeview
        style = ttk.Style()
        style.configure("Treeview",
                        font=('Arial', 10),
                        rowheight=30)  # Base row height
        style.configure("Treeview.Heading",
                        font=('Arial', 12, 'bold'))  # Bold column headers

        # Create vertical scrollbar and link it to the Treeview
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(expand=True, fill='both', side="left")

        # Button to scrape and load jobs
        self.scrape_button = tk.Button(root, text="Scrape and Load Jobs", command=self.scrape_and_load_jobs)
        self.scrape_button.pack(pady=10)

        # Checkbox toggle button
        self.toggle_button = tk.Button(root, text="Toggle Check", command=self.toggle_check)
        self.toggle_button.pack(pady=5)

        # Bind a double-click event on the Treeview to show full description
        self.tree.bind("<Double-1>", self.show_full_description)

        # Initial load of jobs
        self.load_jobs()  # Automatically load jobs from the database at startup

    def sort_column(self, col):
        """Sorts the Treeview by a given column."""
        current_sort_order = self.sort_state.get(col, False)  # Retrieve the current sort order for the column
        new_sort_order = not current_sort_order
        self.sort_state[col] = new_sort_order  # Toggle sort order

        # Retrieve job data from Treeview to sort
        jobs = [(self.tree.item(item)["values"], item) for item in self.tree.get_children()]
        
        # Determine sort key based on column index
        col_idx = self.tree["columns"].index(col)
        jobs.sort(key=lambda job: job[0][col_idx], reverse=new_sort_order)

        # Rearrange items in sorted order
        for index, (_, item) in enumerate(jobs):
            self.tree.move(item, '', index)

    def scrape_and_load_jobs(self):
        """Runs the scraper and loads new job data into the Treeview."""
        # Run the scraper
        self.scraper.scrape_indeed_jobs()
        self.load_jobs()  # Load jobs into Treeview after scraping

    def load_jobs(self):
        """Loads job data from the database into the Treeview."""
        # Clear existing rows in the Treeview
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Connect to the database and fetch jobs
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if the table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs';")
            table_exists = cursor.fetchone()
            
            if not table_exists:
                print("The jobs table does not exist in the database.")
                messagebox.showwarning("Database Error", "The 'jobs' table does not exist in the database.")
                return

            # Fetch jobs data
            cursor.execute("SELECT id, title, location, salary, advantages, description, checked FROM jobs")
            jobs = cursor.fetchall()
            
            if not jobs:
                print("No job data found in the jobs table.")
                messagebox.showinfo("No Data", "No job listings are available in the database.")
            else:
                print(f"Loaded {len(jobs)} jobs from the database.")

            # Insert jobs into the Treeview
            for job in jobs:
                # Convert checked state to True/False for the Treeview
                checked = bool(job[6])  # Database stores 1/0; Treeview expects True/False
                self.tree.insert("", "end", values=(job[0], job[1], job[2], job[3], job[4], job[5], checked))

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            messagebox.showerror("Database Error", f"An error occurred while accessing the database: {e}")
        finally:
            if conn:
                conn.close()

    def toggle_check(self):
        selected_item = self.tree.selection()
        if selected_item:  # Check if an item is selected
            selected_item = selected_item[0]  # Get the first selected item
            current_values = self.tree.item(selected_item, 'values')
            current_value = current_values[6]  # Assuming checkbox is the 7th column
            new_value = not eval(str(current_value))  # Toggle the checkbox state

            # Update the checkbox value in the Treeview
            updated_values = current_values[:6] + (new_value,)
            self.tree.item(selected_item, values=updated_values)
            
            # Save the new state in the database
            self.save_checkbox_state(current_values[0], new_value)
        else:
            messagebox.showinfo("No Selection", "Please select a job entry first.")

    def save_checkbox_state(self, job_id, new_value):
        """Save the new checkbox state to the database."""
        new_value_int = 1 if new_value else 0  # Convert True/False to 1/0 for database

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Update the checkbox state in the database for the corresponding job by ID
            cursor.execute("UPDATE jobs SET checked = ? WHERE id = ?", (new_value_int, job_id))
            conn.commit()
            print(f"Saved checkbox state for job with ID {job_id}: {new_value_int}")

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            messagebox.showerror("Database Error", f"An error occurred while saving the checkbox state: {e}")
        finally:
            if conn:
                conn.close()

    def show_full_description(self, event):
        """Display the full job description in a new window on double-click."""
        selected_item = self.tree.selection()
        if selected_item:
            selected_item = selected_item[0]
            job_details = self.tree.item(selected_item, 'values')
            description = job_details[5]  # Assuming description is in the 6th column

            # Create a new top-level window to display the full description
            description_window = tk.Toplevel(self.root)
            description_window.title("Full Job Description")
            description_window.geometry("400x300")

            # Add a Text widget to show the full description
            text_widget = tk.Text(description_window, wrap='word', font=('Arial', 10))
            text_widget.insert("1.0", description)
            text_widget.config(state='disabled')  # Make text read-only
            text_widget.pack(expand=True, fill='both', padx=10, pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = JobSearchApp(root)
    root.mainloop()
