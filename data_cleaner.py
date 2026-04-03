import pandas as pd 
import os
import re
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime

# ==========================================
# FUTURE ODATA FETCHING LOGIC (COMMENTED)
# ==========================================
# def fetch_odata_from_1c(url, username, password):
#     """
#     Fetches raw JSON or XML data from 1C OData endpoint.
#     Once you have access, you can replace the local file reading 
#     with pandas loading data dynamically from this API request.
#     """
#     try:
#         response = requests.get(url, auth=HTTPBasicAuth(username, password))
#         response.raise_for_status()
#         data = response.json()
#         # df = pd.DataFrame(data['value'])
#         # return df
#     except Exception as e:
#         print(f"Failed to fetch data from 1C: {e}")
#         return None

# day/month/year filter will be renoved after i get the ODATA
def determine_period_type(filename):
    base = filename.replace('.xlsx', '')
    parts = base.split('.')
    
    if len(parts) == 3:
        return 'day'
    elif len(parts) == 2:
        return 'month'
    elif len(parts) == 1:
        return 'year'
    
    return 'unknown'

def clean_file(filepath, output_dir, filename):
    try:
        df = pd.read_excel(filepath)
    except Exception as e:
        print(f"Could not read {filepath}: {e}")
        return

    try:
        df = df[['Unnamed: 1','Unnamed: 2','Total','Unnamed: 4','Unnamed: 5','Unnamed: 6','Unnamed: 8']]
        
        df = df.rename(columns={
            'Unnamed: 1': 'code',                   
            'Unnamed: 2': 'product_name',           
            'Total': 'remained_product',          
            'Unnamed: 4' : 'quantity',              
            'Unnamed: 5' : 'price',                 
            'Unnamed: 6' : 'sales_without_discount',
            'Unnamed: 8' : 'sales'                  
        })
        
        df = df.drop([0,1,2])
        
        
        if len(df) > 0:
            df = df.drop(df.index[-1])
            

        cols_to_convert = ['remained_product', 'price', 'sales_without_discount', 'sales']
        for col in cols_to_convert:
            df[col] = df[col].astype(str).str.replace(',', '', regex=False).astype(float).fillna(0).astype(int)
            
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0).astype(int)

        out_path = os.path.join(output_dir, filename)
        
        os.makedirs(output_dir, exist_ok=True)
        
        df.to_excel(out_path, index=False)
        print(f"Successfully cleaned and saved to {out_path}")
        
        return df

    except Exception as e:
        print(f"Error processing matching columns in {filename}: {e}")
        return None

def process_all_raw_data():
    raw_dir = 'raw_data'
    if not os.path.exists(raw_dir):
        print(f"Directory {raw_dir} does not exist.")
        return

    for filename in os.listdir(raw_dir):
        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            period = determine_period_type(filename)
            
            if period == 'unknown':
                print(f"Skipping unknown format: {filename}")
                continue
            
            filepath = os.path.join(raw_dir, filename)
            
            output_dir = os.path.join('clean_data', period)
            
            clean_file(filepath, output_dir, filename)

if __name__ == "__main__":
    process_all_raw_data()
