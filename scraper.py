import time
import random
import sqlite3
import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

# Set up logging
logging.basicConfig(filename='job_scraper.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class JobScraper:
    def __init__(self, db_path='data/jobs.db'):
        self.base_indeed_url = "https://www.indeed.fr"
        self.db_path = db_path
        self.create_database()

        # Set up Selenium options
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36")

        # Initialize the WebDriver
        self.driver = webdriver.Chrome(service=Service("C:\\Users\\Utilisateur\\chromedriver-win64\\chromedriver.exe"), options=options)

    def create_database(self):
        """Creates a SQLite database to store job data if it doesn't exist."""
        if not os.path.exists(self.db_path):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                location TEXT NOT NULL,
                salary TEXT,
                advantages TEXT,
                description TEXT
            )''')
            conn.commit()
            conn.close()
            logging.info(f"Database '{self.db_path}' and 'jobs' table created successfully.")

    def save_to_database(self, job):
        """Saves a job to the SQLite database if the title doesn't already exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM jobs WHERE title = ?', (job['title'],))
        exists = cursor.fetchone()[0]

        if not exists:
            cursor.execute('''INSERT INTO jobs (title, location, salary, advantages, description) 
                              VALUES (?, ?, ?, ?, ?)''', (
                job['title'], job['location'], job['salary'], job['advantages'], job['description']
            ))
            conn.commit()
            logging.info(f"Job '{job['title']}' saved to database.")
            conn.close()
            return False  # New job saved
        else:
            logging.info(f"Job '{job['title']}' already exists in the database, skipping.")
            conn.close()
            return True  # Duplicate job found

    def close_cookie_popup(self, wait):
        """Closes the cookie consent popup if present."""
        try:
            cookie_popup = wait.until(EC.presence_of_element_located((By.ID, "onetrust-accept-btn-handler")))
            cookie_popup.click()
            logging.info("Cookie consent popup closed.")
        except TimeoutException:
            logging.info("No cookie consent popup found.")

    def detect_captcha(self, wait):
        """Detects if a CAPTCHA is present and pauses for manual completion."""
        try:
            captcha = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'captcha')]")))
            if captcha:
                logging.warning("CAPTCHA detected. Waiting for manual completion...")
                input("Please complete the CAPTCHA, then press Enter to continue...")
        except TimeoutException:
            logging.info("No CAPTCHA detected on the page.")

    def scrape_indeed_jobs(self):
        """Scrapes jobs from Indeed."""
        logging.info("Navigating to Indeed...")
        self.driver.get(self.base_indeed_url)
        time.sleep(2)  # Allow some time for the page to load

        wait = WebDriverWait(self.driver, 20)
        logging.info("Page loaded, now checking for CAPTCHA...")
        
        # Detect and handle CAPTCHA if present
        self.detect_captcha(wait)
        
        logging.info("Checking for search elements...")

        # Close cookie popup if present
        self.close_cookie_popup(wait)

        try:
            search_box = wait.until(EC.visibility_of_element_located((By.ID, "text-input-what")))
            location_box = wait.until(EC.visibility_of_element_located((By.ID, "text-input-where")))

            search_terms = "développeur fullstack, développeur web, ingénieur logiciel"
            location_terms = "Ile-de-France, Paris"

            search_box.clear()
            location_box.clear()
            search_box.send_keys(search_terms)
            location_box.send_keys(location_terms)
            location_box.submit()

            time.sleep(random.uniform(3, 6))

            jobs = []
            while True:  # Loop for pagination
                job_cards = self.driver.find_elements(By.CSS_SELECTOR, '.job_seen_beacon')
                duplicate_found = False

                for job_card in job_cards:
                    try:
                        job_card.click()
                        time.sleep(random.uniform(2, 4))

                        # Scroll to load job details
                        self.scroll_to_load_details()

                        job_data = {
                            'title': self.get_job_title(),
                            'salary': self.get_job_salary(),
                            'location': self.get_location(),
                            'advantages': self.get_advantages(),
                            'description': self.get_job_description()
                        }

                        # Save job to database and log details for debugging
                        is_duplicate = self.save_to_database(job_data)
                        jobs.append(job_data)
                        logging.info(f"Scraped job from Indeed: {job_data}")

                        # If duplicate found, mark and break out of loop
                        if is_duplicate:
                            duplicate_found = True
                            break

                        # Go back to the previous page to access the next job
                        self.driver.back()
                        time.sleep(random.uniform(2, 4))  # Wait after returning to results page
                    except Exception as e:
                        logging.error("Error occurred while processing a job card.")
                        logging.exception(e)

                # If duplicate was found, attempt to go to the next page
                if duplicate_found:
                    try:
                        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@aria-label='Suivant']")))
                        next_button.click()
                        time.sleep(random.uniform(3, 6))  # Allow the next page to load
                    except TimeoutException:
                        logging.info("No more pages found or it timed out. Ending scrape.")
                        break
                else:
                    # If no duplicates were found on this page, continue scraping
                    continue

            return jobs
        except Exception as e:
            logging.error("Error occurred while scraping Indeed jobs.")
            logging.exception(e)
            return []

    def scroll_to_load_details(self):
        """Scrolls down the job detail page to load all content."""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)  # Pause to allow content to load
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        logging.info("Scrolled to load all job details.")

    def get_job_title(self):
        """Extracts the job title from the job description page."""
        try:
            title_element = self.driver.find_element(By.XPATH, "//h2[contains(@class, 'jobsearch-JobInfoHeader-title')]")
            return title_element.text.strip()
        except NoSuchElementException:
            logging.warning("Job title not found.")
            return "N/A"
    
    def get_job_salary(self):
        """Extracts the job title from the job description page."""
        try:
            title_element = self.driver.find_element(By.XPATH, "//div[contains(@id, 'salaryInfoAndJobType')]")
            return title_element.text.strip()
        except NoSuchElementException:
            logging.warning("Job salary not found.")

    def get_location(self):
        """Extracts location from the job posting."""
        try:
            location_element = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="inlineHeader-companyLocation"]')
            return location_element.text.strip()
        except NoSuchElementException:
            logging.warning("Location not found.")
            return "N/A"

    def get_advantages(self):
        """Extracts advantages from the job posting."""
        try:
            advantages_element = self.driver.find_element(By.ID, "benefits")
            return advantages_element.text.strip()
        except NoSuchElementException:
            logging.warning("No advantages found.")
            return "N/A"

    def get_job_description(self):
        """Extracts the job description."""
        try:
            description_element = self.driver.find_element(By.ID, "jobDescriptionText")
            return description_element.text.strip()
        except NoSuchElementException:
            logging.warning("Job description not found.")
            return "N/A"

    def close(self):
        """Closes the WebDriver."""
        self.driver.quit()
        logging.info("WebDriver closed.")

if __name__ == "__main__":
    scraper = JobScraper()
    try:
        scraper.scrape_indeed_jobs()
    finally:
        scraper.close()
