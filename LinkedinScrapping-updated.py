# importing libraries
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import logging
from dotenv import load_dotenv
# importing libraries to plot the wordcloud
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


# Variables - Load from environment variables
## Linkedin ID and PASSWORD
email = os.getenv('LINKEDIN_EMAIL')
password = os.getenv('LINKEDIN_PASSWORD')

if not email or not password:
    raise ValueError("Please set LINKEDIN_EMAIL and LINKEDIN_PASSWORD in your .env file")

## Write here the job position and local for search
position = os.getenv('JOB_POSITION', 'data scientist')
local = os.getenv('JOB_LOCATION', 'brazil')

logger.info(f"Searching for '{position}' jobs in '{local}'")

## formating to linkedin model
position = position.replace(' ', "%20")




# Open browser with modern webdriver-manager
logger.info("Initializing Chrome browser...")
service = Service(ChromeDriverManager().install())
options = webdriver.ChromeOptions()
options.add_argument('--headless')  # Run in headless mode
options.add_argument('--no-sandbox')  # Required for running as root
options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
options.add_argument('--disable-gpu')  # Disable GPU hardware acceleration
options.add_argument('--start-maximized')
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 10)  # 10 second timeout for explicit waits

# Opening linkedin website
logger.info("Navigating to LinkedIn login page...")
driver.get('https://www.linkedin.com/login')

# Wait for login elements and enter credentials
logger.info("Logging in to LinkedIn...")
username_field = wait.until(EC.presence_of_element_located((By.ID, 'username')))
password_field = wait.until(EC.presence_of_element_located((By.ID, 'password')))

username_field.send_keys(email)
password_field.send_keys(password)
password_field.send_keys(Keys.RETURN)

# Wait for redirect after login
time.sleep(3)

# Opening jobs webpage
logger.info("Navigating to job search results...")
driver.get(
    f"https://www.linkedin.com/jobs/search/?currentJobId=2662929045&geoId=106057199&keywords={position}&location={local}")

# Wait for job listings to load
wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'scaffold-layout__list-container')))


# creating a list where the descriptions will be stored
disc_list = []
total_jobs_scraped = 0

logger.info("Starting job scraping process...")

try:
    for i in range(1, 41):
        try:
            # click button to change the job list
            logger.info(f'Processing Page {i}/40')

            # Wait for pagination button and click
            page_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, f'//button[@aria-label="Page {i}"]'))
            )
            page_button.click()
            time.sleep(2)

            # Wait for job list to load
            jobs_lists = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, 'scaffold-layout__list-container'))
            )

            jobs = jobs_lists.find_elements(By.CLASS_NAME, 'jobs-search-results__list-item')
            logger.info(f'Found {len(jobs)} jobs on page {i}')

            time.sleep(1)

            # Loop through each job on the page
            for job in range(1, len(jobs)+1):
                try:
                    logger.info(f'Scraping job {job}/{len(jobs)} on page {i}')

                    # Click on the job listing
                    job_item = wait.until(
                        EC.element_to_be_clickable(
                            (By.XPATH, f'/html/body/div[5]/div[3]/div[4]/div/div/main/div/section[1]/div/ul/li[{job}]')
                        )
                    )
                    job_item.click()
                    time.sleep(1)

                    # Click on job title to expand details
                    try:
                        job_link = driver.find_element(
                            By.XPATH,
                            f'/html/body/div[5]/div[3]/div[4]/div/div/main/div/section[1]/div/ul/li[{job}]/div/div[1]/div[1]/div[2]/div[1]/a'
                        )
                        job_link.click()
                        time.sleep(1.5)
                    except Exception as e:
                        logger.warning(f"Could not click job link: {e}")

                    # Wait for and get job description
                    job_desc = wait.until(
                        EC.presence_of_element_located((By.ID, 'job-details'))
                    )

                    soup = BeautifulSoup(job_desc.get_attribute('outerHTML'), 'html.parser')
                    disc_list.append(soup.text)
                    total_jobs_scraped += 1

                except Exception as e:
                    logger.error(f"Error scraping job {job} on page {i}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error processing page {i}: {e}")
            continue

except KeyboardInterrupt:
    logger.info("Scraping interrupted by user")
except Exception as e:
    logger.error(f"Fatal error during scraping: {e}")
finally:
    logger.info(f"Scraping completed. Total jobs scraped: {total_jobs_scraped}")
    driver.quit()


# Creating a Dataframe with list
logger.info("Processing scraped data...")

if len(disc_list) == 0:
    logger.error("No job descriptions were scraped. Exiting.")
    exit(1)

df = pd.DataFrame(disc_list)
logger.info(f"Created dataframe with {len(df)} job descriptions")

# deleting useless words
word_list = ['Expect', 'Qualifications', 'Required', 'expected', 'Responsibilities', 'Requisitos', 'Requirements', 'Qualificações', 'QualificationsRequired1', 'você deve ter:', 'experiência', 'você:',
             'Desejável', 'great', 'Looking For', 'll Need', 'Conhecimento', 'se:', 'habilidades', 'se:', 'REQUISITOS']
# deleting useless words
df = df.replace(f'\n', '', regex=True)

for i in range (0, len(word_list)):
    df = df.replace(f'^.*?{word_list[i]}', '', regex=True)

logger.info("Data cleaning completed")


# setup wordcloud
logger.info("Generating wordcloud...")
stopwords = set(STOPWORDS)
# selecting useless words
badwords = {'gender', 'experience', 'application', 'Apply', 'salary', 'todos', 'os', 'company', 'identity', 'sexual', 'orientation',
            'de', 'orientação', 'sexual', 'gênero', 'committed', 'toda', 'client', 'conhecimento',
            'world', 'year', 'save', 'São', 'Paulo', 'information', 'e', 'orientação', 'sexual', 'equal', 'oppotunity', 'ambiente', 'will',
            'Experiência', 'national origin', 'todas', 'work', 'de', 'da', 'years', 'pessoa', 'clients', 'Plano', 'creating',
            'employer', 'saúde', 'em', 'working', 'pessoas', 'mais', 'data', 'people', 'dia', 'one', 'knowledges', 'plataforma',
            'ou', 'benefício', 'para', 'software', 'opportunity', 'tecnologia', 'você', 'mais', 'solution', 'national', 'origin',
            'trabalhar', 'option', 'negócio', 'empresa', 'o', 'sicence', 'team', 'é', 'veteran', 'status', 'etc', 'raça', 'cor', 'belive',
            'nossa', 'uma', 'como', 'Scientist', 'ferramenta', 'projeto', 'que', 'job', 'benefícios', 'knowledge', 'toll', 's', 'modelo',
            'desconto', 'cultura', 'serviço', 'time', 'se', 'solutions', 'mercado', 'das', 'somos', 'problema', 'mundo', 'race', 'color',
            'vaga', 'pelo', 'ser', 'show', 'Seguro', 'Se', 'um', 'Um', 'tool', 'regard', 'without', 'make', 'ao', 'técnica', 'life',
            'interested', 'diversidade', 'proud', 'ability', 'sobre', 'options', 'using', 'área', 'nosso', 'na', 'seu', 'product', 'produto',
            'building', 'skill', 'model', 'religion', 'Share', 'receive', 'consideration', 'Aqui', 'vida', 'ferramentas', 'Vale', 'Refeição',
            'Strong', 'Pay', 'range', 'available', 'part', 'trabalho', 'Alimentação', 'employment', 'qualified', 'applicants', 'gympass',
            'está', 'comprometida', 'forma', 'Transporte', 'Yes', 'gente', 'melhor', 'lugar', 'believe', 'moment', 'próximo', 'deasafio',
            'dos', 'oportunidade', 'idade', 'new', 'Try', 'Premium', 'deficiência', 'sempre', 'criar', 'employee', 'problemas', 'unavailable',
            'Brasil', 'dado', 'hiring', 'trends', 'equipe', 'recent', 'temos', 'build', 'career', 'nós', 'diferencial', 'ma',
            'total', 'oferecemos', 'contato', 'tem', 'não', 'free', 'Full'}

# deleting the useless words on plot
stopwords.update(badwords)

# plot parameters
wordcloud = WordCloud(background_color='black',
                      width=1600, height=800,
                      stopwords=stopwords,
                      max_words=100,
                      max_font_size=250,
                      random_state=42).generate("".join(df[0]))

# Plot
logger.info("Saving wordcloud image...")
plt.tight_layout(pad=0)
plt.imshow(wordcloud, interpolation='bilinear')
plt.savefig('wordcloud-job.png', dpi=300)
plt.axis("off")
logger.info("Wordcloud saved as 'wordcloud-job.png'")

# exporting our dataframe to a csv file
logger.info("Exporting data to CSV...")
df.to_csv('wordcloud-job.csv', sep=';')
logger.info("Data exported to 'wordcloud-job.csv'")

logger.info("Process completed successfully!") 
