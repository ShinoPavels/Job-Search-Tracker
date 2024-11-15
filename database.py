import sqlite3

class Database:
    def __init__(self, db_name='jobs.db'):
        self.connection = sqlite3.connect(db_name)
        self.create_jobs_table()

    def create_jobs_table(self):
        """Creates the jobs table with an additional 'checked' column for job status."""
        with self.connection:
            self.connection.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    location TEXT NOT NULL,
                    advantages TEXT NOT NULL,
                    salary TEXT NOT NULL,
                    description TEXT NOT NULL,
                    checked INTEGER DEFAULT 0  -- This stores the checkbox state (0 = unchecked, 1 = checked)
                )
            ''')

    def store_job_data(self, job_data):
        """Inserts job data into the jobs table, ensuring no null values are stored."""
        # Ensure no null values by replacing them with empty strings
        job_data = {
            'title': job_data.get('title', '') or '',
            'location': job_data.get('location', '') or '',
            'advantages': job_data.get('advantages', '') or '',
            'salary': job_data.get('salary', '') or '',
            'description': job_data.get('description', '') or ''
        }

        with self.connection:
            self.connection.execute('''
                INSERT INTO jobs (title, location, advantages, salary, description)
                VALUES (:title, :location, :advantages, :salary, :description)
            ''', job_data)

    def update_checkbox_state(self, job_id, checked_state):
        """Updates the checked state of a job entry by job ID."""
        # Convert True/False to 1/0 for saving in database
        checked_state_int = 1 if checked_state else 0
        
        with self.connection:
            self.connection.execute('''
                UPDATE jobs
                SET checked = ?
                WHERE id = ?
            ''', (checked_state_int, job_id))

    def load_jobs_with_state(self):
        """Loads all job records with their checked status, converting checked to boolean."""
        cursor = self.connection.cursor()
        cursor.execute('SELECT * FROM jobs')
        jobs = cursor.fetchall()

        # Convert checked field from 0/1 to False/True in the result
        jobs_with_state = [
            (job[0], job[1], job[2], job[3], job[4], job[5], bool(job[6]))  # Convert checked (0/1) to boolean
            for job in jobs
        ]

        return jobs_with_state

    def close(self):
        """Closes the database connection."""
        self.connection.close()
