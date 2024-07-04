import urllib3
import zipfile
import os
import pandas as pd
from bs4 import BeautifulSoup
from io import BytesIO
import requests
import re

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

fiberCopPage = 'https://www.fibercop.it/chi-siamo/verifica-la-tua-copertura/'
stringHtml = 'Elenco CRO/CNO attivi'
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'
}

def update_readme_date(filepath, new_date):
    with open(filepath, 'r') as file:
        content = file.read()
    
    # Regular expression to find the date in the format YYYY-MM-DD
    old_date_pattern = r'Dati aggiornati al: `\d{4}-\d{2}-\d{2}`'
    
    # Replacement string with the new date
    new_date_string = f'Dati aggiornati al: `{new_date}`'
    
    # Replace the old date with the new date
    updated_content = re.sub(old_date_pattern, new_date_string, content)
    
    if updated_content != content:
        # Write the updated content back to the file
        with open(filepath, 'w') as file:
            file.write(updated_content)
        

def extract_filename_date(filename):
    pattern = r'(\d{4})(\d{2})(\d{2})'
    
    match = re.search(pattern, filename)
    
    if match:
        year, month, day = match.groups()
        
        # Format the date as YYYY-MM-DD
        extracted_date = f'{year}-{month}-{day}'
        return extracted_date
    else:
        return None

def fetch_data():
    try:
        print('Downloading started')
        reqHtml = requests.get(fiberCopPage, headers=headers, verify=False)
        reqHtml.raise_for_status()

        soup = BeautifulSoup(reqHtml.content, 'html.parser')

        # Find the link to the ZIP file
        for a in soup.find_all('a', href=True, string=stringHtml):
            urlZip = a['href']
            break  # Assuming there's only one link matching the criteria
        
        if urlZip is not None:
            print('Downloading from URL: ' + urlZip)
            # Fetch the ZIP file content
            req = requests.get(urlZip, headers=headers, verify=False)
            return req.content
        
        return None

    except Exception as e:
        print(f"Error: {e}")
        return None

def clear_temp_folder(tempFolder):
    print("Clearing temp folder")
    for f in os.listdir(tempFolder):    
        os.remove(os.path.join(tempFolder, f))
        os.makedirs(tempFolder)
    print("Temp folder cleared")
    
def process_data(zip_content):
    tempFolder = '/tmp'
    csvTime = None
    

    if not os.path.exists(tempFolder):
        os.makedirs(tempFolder)
    else:
        clear_temp_folder(tempFolder)

    with zipfile.ZipFile(BytesIO(zip_content)) as zipObj:
        zipObj.extractall(tempFolder)
        for file in os.listdir(tempFolder):
            if file.endswith(".csv"):
                
                csvpath = os.path.join(tempFolder, file)
                csvTime = extract_filename_date(csvpath)

                print("CSV Creation Date: ", csvTime)
                break

    if not csvpath:
        raise Exception("No CSV Found!")
        
    # Load only necessary columns
    columns = ['PROVINCIA', 'COMUNE', 'LATITUDINE', 'LONGITUDINE', 'CENTRALE_TX_DI_RIF', 'ID_ELEMENTO',
               'TIPO', 'TIPOLOGIA_CRO', 'STATO', 'INDIRIZZO', 'DATA_PUBBLICAZIONE']
    
    try:
        list_cantieri = pd.read_csv(csvpath, delimiter=';', usecols=columns).dropna()
        list_cantieri = list_cantieri.sort_values(by=['PROVINCIA', 'COMUNE', 'INDIRIZZO'])
    except:
        clear_temp_folder(tempFolder)
        raise Exception("Error parsing CSV!")
    
    clear_temp_folder(tempFolder)
    return csvTime, list_cantieri.to_dict(orient='records')

if __name__ == "__main__":
    zip_content = fetch_data()
    
    if zip_content is not None:
        creation_time, data = process_data(zip_content)
        # Save data to a JSON file
        with open('data.json', 'w') as f:
            import json
            json.dump({"creation_time": creation_time, "data": data}, f)
        
        if creation_time is not None:
            update_readme_date('README.md', creation_time)