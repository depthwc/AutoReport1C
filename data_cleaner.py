import pandas as pd 
import os
from datetime import datetime



"""

there should be dynamicly data donwloading

"""



# today = datetime.now()
# formatted = today.strftime("%d.%m.%Y")

# file_name = formatted+".xlsx"

file_name = "30.03.2026.xlsx"

df = pd.read_excel(f'raw_data/{file_name}')

print(df.columns)

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
df = df.drop(df.index[-1])


# data converting
cols_to_convert = ['remained_product', 'price', 'sales_without_discount', 'sales']
for col in cols_to_convert:
    df[col] = df[col].astype(str).str.replace(',', '', regex=False).astype(float).fillna(0).astype(int)



df.to_excel(f"clean_data/{file_name}", index=False)

print(df)