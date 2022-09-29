import os
from dotenv import load_dotenv

load_dotenv()

Linkedin_id = os.getenv('Linked_in_id')
Linkedin_pass = os.getenv('Linked_in_pass')

print(Linkedin_id, Linkedin_pass)