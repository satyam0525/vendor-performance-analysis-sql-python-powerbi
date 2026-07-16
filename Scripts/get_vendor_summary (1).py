import sqlite3
import pandas as pd
import logging
from ingestion_db import ingest_db

logging.basicConfig(
    filename = "logs/get_vendor_summary.log",
    level = logging.DEBUG,
    format = "%(asctime)s - %(levelname)s - %(message)s",
    filemode = "a"
)

def create_vendor_summary(conn):
    """this function will merge the different tables to get the overall vendor summary and adding new column in the resultant data"""

    vendor_sales_summary = pd.read_sql_query("""WITH FreightSummary AS (
        select 
            VendorNumber, 
            SUM(freight) as FreightCost 
        FROM vendor_invoice 
        GROUP BY VendorNumber
    ),
    
    purchaseSummary as (
        Select
            p.VendorNumber,
            p.VendorName,
            p.Brand,
            p.Description,
            p.PurchasePrice,
            pp.Price as ActualPrice,
            pp.Volume,
            SUM(p.Quantity) as TotalPurchaseQuantity,
            SUM(p.Dollars) as TotalPurchaseDollars
        from purchases p
        JOIN purchase_prices pp
            ON p.Brand = pp.Brand
        WHERE p.purchaseprice > 0
        GROUP BY p.vendorNumber, p.VendorName, p.Brand,p.Description,pp.Price,pp.Volume
        
    ),
    
    salesSummary as (
        SELECT
            VendorNo,
            Brand,
            SUM(SalesQuantity) as TotalSalesQuantity,
            SUM(SalesDollars) as TotalSalesDollars,
            SUM(SalesPrice) as TotalSalesPrice,
            SUM(ExciseTax) as TotalExciseTax
        FROM sales
        GROUP BY VendorNo,Brand
        
    )
    
    SELECT 
        ps.VendorNumber,
        ps.VendorName,
        ps.Brand,
        ps.Description,
        ps.PurchasePrice,
        ps.ActualPrice,
        ps.Volume,
        ps.TotalPurchaseQuantity,
        ps.TotalPurchaseDollars,
        ss.TotalSalesQuantity,
        ss.TotalSalesDollars,
        ss.TotalSalesPrice,
        ss.TotalExciseTax,
        fs.FreightCost
    FROM PurchaseSummary ps 
    LEFT JOIN SalesSummary ss
        ON ps.VendorNumber = ss.VendorNo
        AND ps.Brand = ss.Brand
    LEFT JOIN FreightSummary fs
        ON ps.VendorNumber = fs.VendorNumber
    ORDER BY ps.TotalPurchaseDollars DESC""", conn)

    return vendor_sales_summary

def clean_data(df):
    '''this function will clean the data'''
    # changing datatype to float
    df['Volume'] = df['Volume'].astype('float')

    # filling missing value with 0
    df.fillna(0,inplace = True)

    #removing space from categorical columns
    df['VendorName'] = df['VendorName'].str.strip()
    df['Description'] = df['Description'].str.strip()

    #creating new column for better analysis
    df['GrossProfit']= df['TotalSalesDollars']- df['TotalPurchaseDollars']
    df['ProfitMargin'] = df['GrossProfit']/ df['TotalSalesDollars']*100
    df['StockTurnOver'] = df['TotalSalesQuantity']/df['TotalPurchaseQuantity']
    df['SaleToPurchaseRatio'] = df['TotalSalesQuantity']/df['TotalPurchaseDollars']

    return df

if __name__ == '__main__':
    #creating database connection
    conn = sqlite3.connect('inventory.db')

    logging.info('Creating Vendor Summary Table.....')
    summary_df = creating_vendor_summary(conn)
    logging.info(summary.df.head())

    logging.info('Cleaning Data.....')
    clean_df = clean_data(summary_df)
    logging.info(clean_df.head())

    logging.info('Ingesting Data.....')
    ingest_db(clean_df, 'vendor_sales_summary',conn)
    logging.info('Completed')
