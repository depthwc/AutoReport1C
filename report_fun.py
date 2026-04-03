import pandas as pd


# Filter
def get_top_products(df: pd.DataFrame, sort_by: str = 'quantity', head: int = 10, ascending: bool = False):
    if df is None or df.empty:
        return pd.DataFrame()

    required_cols = ['code', 'product_name', 'quantity', 'price', 'sales']
    
    cols = [c for c in required_cols if c in df.columns]
    
    if sort_by not in df.columns:
        return pd.DataFrame() 

    return df[cols].sort_values(by=sort_by, ascending=ascending).head(head)



# Calumn changhe
def get_table_info(df: pd.DataFrame):
    if df is None or df.empty:
        return pd.DataFrame()
    return df.rename(columns={
        'code': 'Raqami',                          
        'product_name': 'Maxsulot nomi',           
        'remained_product': 'Qolgan maxsulot',      
        'quantity': 'Nechta sotilgani',             
        'price': 'Narxi',                          
        'sales_without_discount': 'Chegirmasiz sotuv', 
        'sales': 'Sotuv'                            
    })
