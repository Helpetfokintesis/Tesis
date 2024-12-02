from dotenv import load_dotenv
import os

load_dotenv() # load the environment variables from the .env file

api_key = os.getenv('OPENAI_API_KEY')

# use the openai_api_key variable in your code<<

print(api_key)