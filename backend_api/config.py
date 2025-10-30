from dotenv import load_dotenv
import os

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

API_KEY = os.getenv('API_KEY')
WSDL_URL = os.getenv('WSDL_URL')