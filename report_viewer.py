from numpy import median
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, date
import os


file_name = "30.03.2026.xlsx"

maindf = pd.read_excel(f"clean_data/{file_name}")

daily_info = pd.read_excel("cash_register/daily_info.xlsx")

# data converting
cols_to_convert = ['remained_product', 'price', 'sales_without_discount', 'sales']
for col in cols_to_convert:
    maindf[col] = maindf[col].astype(str).str.replace(',', '', regex=False).astype(float).fillna(0)# .astype(int)




sum_quantity = maindf['quantity'].sum()
sum_sales_discount = maindf['sales_without_discount'].sum()
sum_sales = maindf['sales'].sum()

top10_mostsold_product = maindf[['code','product_name','quantity','price','sales']].sort_values(by='quantity', ascending=False).head(10)
top10_mostincome_product = maindf[['code','product_name','quantity','price','sales']].sort_values(by='sales', ascending=False).head(10)

table_info = maindf.rename(columns={
    'code': 'Raqami',
    'product_name': 'Maxsulot nomi',
    'remained_product': 'Qolgan maxsulot',
    'quantity' : 'Nechta sotilgani',
    'price': 'Narxi',
    'sales_without_discount': 'Chegirmasiz sotuv',
    'sales': 'Sotuv'
})

print(daily_info)
