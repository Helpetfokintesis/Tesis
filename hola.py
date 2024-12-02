from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# Configuración de las opciones del navegador
chrome_options = Options()
chrome_options.add_argument("--headless")  # Opcional: ejecutar en modo sin cabeza
chrome_options.add_argument("--disable-gpu")  # Opcional: desactiva la GPU

# Inicializar el navegador con el ChromeDriver adecuado
driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)

# Abre la página de Google para probar la instalación
driver.get("https://www.google.com")
print(driver.title)  # Deberías ver "Google" como resultado

# Cierra el navegador
driver.quit()
