import pandas as pd
import panel as pn
import hvplot.pandas
import os

pn.extension()  # Initialize Panel without bootstrap template

# 1. Load the Data
file_path = '/Users/yangguang/Desktop/Intel/Intel_Financial_Data.xlsx'

try:
    # Load all sheets into a dictionary of DataFrames
    df_dict = pd.read_excel(file_path, sheet_name=None)

    # Extract DataFrames
    income_statement = df_dict['Income Statement']
    balance_sheet = df_dict['Balance Sheet']
    cash_flow_statement = df_dict['Cash Flow Statement']
    quarterly_stock_data = df_dict['Quarterly Stock Data']

    print("Data loaded successfully!")

except FileNotFoundError:
    print(f"Error: The file '{file_path}' was not found. Make sure it's in the correct directory.")
    exit()
except KeyError as e:
    print(f"Error: Sheet name '{e}' not found in the Excel file. Please check sheet names.")
    exit()
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    exit()

# 2. Data Cleaning
# Fill NaN values with 0 and ensure 'fiscalDateEnding'/'Quarter End Date' is datetime
for df in [income_statement, balance_sheet, cash_flow_statement]:
    df['fiscalDateEnding'] = pd.to_datetime(df['fiscalDateEnding'])
    df.set_index('fiscalDateEnding', inplace=True)
    df.fillna(0, inplace=True)

quarterly_stock_data['Quarter End Date'] = pd.to_datetime(quarterly_stock_data['Quarter End Date'])
quarterly_stock_data.set_index('Quarter End Date', inplace=True)
quarterly_stock_data.fillna(0, inplace=True)

# Convert numeric columns to float and scale to Million USD (except EPS, which is per share)
def scale_to_millions(df, columns):
    for col in columns:
        if col in df.columns:
            df[col] = df[col].astype(float) / 1_000_000  # Convert to Million USD

income_metrics = ['totalRevenue', 'operatingIncome', 'depreciation', 'depreciationAndAmortization', 'netIncome']
balance_metrics = ['totalAssets', 'propertyPlantEquipment', 'totalLiabilities', 'totalCurrentLiabilities', 'totalShareholderEquity']
cashflow_metrics = ['capitalExpenditures', 'cashflowFromInvestment', 'cashflowFromFinancing', 'dividendPayout']

scale_to_millions(income_statement, income_metrics)
scale_to_millions(balance_sheet, balance_metrics)
scale_to_millions(cash_flow_statement, cashflow_metrics)

# Fix typos in column names
if 'opeartingIncome' in income_statement.columns:
    income_statement.rename(columns={'opeartingIncome': 'operatingIncome'}, inplace=True)
if 'capitalExpenditure' in cash_flow_statement.columns:
    cash_flow_statement.rename(columns={'capitalExpenditure': 'capitalExpenditures'}, inplace=True)

# 3. Individual Visualizations for Original Dashboard
def create_plot(df, metric, title, ylabel='Million USD'):
    if metric in df.columns:
        return df.hvplot.line(
            x=df.index.name, y=metric, 
            title=title, 
            ylabel=ylabel, xlabel='Date',
            rot=45, width=600, height=400
        )
    else:
        return pn.pane.Markdown(f"Metric '{metric}' not found in data.")

# Income Statement Plots
income_plots = [
    create_plot(income_statement, 'totalRevenue', 'Total Revenue Over Time'),
    create_plot(income_statement, 'operatingIncome', 'Operating Income Over Time'),
    create_plot(income_statement, 'depreciation', 'Depreciation Over Time'),
    create_plot(income_statement, 'depreciationAndAmortization', 'Depreciation and Amortization Over Time'),
    create_plot(income_statement, 'netIncome', 'Net Income Over Time')
]

# Balance Sheet Plots
balance_plots = [
    create_plot(balance_sheet, 'totalAssets', 'Total Assets Over Time'),
    create_plot(balance_sheet, 'propertyPlantEquipment', 'Property, Plant, and Equipment Over Time'),
    create_plot(balance_sheet, 'totalLiabilities', 'Total Liabilities Over Time'),
    create_plot(balance_sheet, 'totalCurrentLiabilities', 'Total Current Liabilities Over Time'),
    create_plot(balance_sheet, 'totalShareholderEquity', 'Total Shareholder Equity Over Time')
]

# Cash Flow Statement Plots
cashflow_plots = [
    create_plot(cash_flow_statement, 'capitalExpenditures', 'Capital Expenditures Over Time'),
    create_plot(cash_flow_statement, 'cashflowFromInvestment', 'Cash Flow from Investment Over Time'),
    create_plot(cash_flow_statement, 'cashflowFromFinancing', 'Cash Flow from Financing Over Time'),
    create_plot(cash_flow_statement, 'dividendPayout', 'Dividend Payout Over Time')
]

# 4. Original Dashboard Layout
original_dashboard = pn.Column(
    '# Intel Financial Data Dashboard',
    pn.pane.Markdown('## Income Statement Metrics'),
    *income_plots,
    pn.pane.Markdown('## Balance Sheet Metrics'),
    *balance_plots,
    pn.pane.Markdown('## Cash Flow Statement Metrics'),
    *cashflow_plots,
    sizing_mode='stretch_width'
)

# 5. Key Metrics Dashboard
merged_df = income_statement[['netIncome']].join(cash_flow_statement[['dividendPayout']], how='inner')

new_dashboard = pn.GridSpec(sizing_mode='stretch_both', max_width=1000, max_height=800)

# 1. Histogram of Dividend Payout
dividend_hist = cash_flow_statement.hvplot.hist(
    y='dividendPayout', 
    title='Distribution of Dividend Payout', 
    ylabel='Count', xlabel='Dividend Payout (Million USD)',
    width=400, height=400
)
new_dashboard[0, 0] = dividend_hist

# 2. EPS Over Time (Line Plot)
eps_line = quarterly_stock_data.hvplot.line(
    x='Quarter End Date', y='EPS', 
    title='EPS Over Time', 
    ylabel='EPS (USD)', xlabel='Date',
    rot=45, width=400, height=400
)
new_dashboard[0, 1] = eps_line

# 3. Capital Expenditures Over Time (Line Plot)
capex_line = cash_flow_statement.hvplot.line(
    x='fiscalDateEnding', y='capitalExpenditures', 
    title='Capital Expenditures Over Time', 
    ylabel='Million USD', xlabel='Date',
    rot=45, width=400, height=400
)
new_dashboard[1, 0] = capex_line

# 4. Net Income vs Dividend Payout (Scatter Plot)
netincome_dividend_scatter = merged_df.hvplot.scatter(
    x='netIncome', y='dividendPayout', 
    title='Net Income vs Dividend Payout', 
    xlabel='Net Income (Million USD)', ylabel='Dividend Payout (Million USD)',
    width=400, height=400
)
new_dashboard[1, 1] = netincome_dividend_scatter

# 6. New Heatmap Dashboard for Net Income vs Dividend Payout
def create_netincome_dividend_heatmap():
    # Use merged_df with netIncome and dividendPayout
    heatmap_data = merged_df[['netIncome', 'dividendPayout']].copy()
    
    # Create a hexbin heatmap (2D histogram)
    heatmap = heatmap_data.hvplot.hexbin(
        x='netIncome', y='dividendPayout',
        title='Net Income vs Dividend Payout Heatmap',
        xlabel='Net Income (Million USD)', ylabel='Dividend Payout (Million USD)',
        width=600, height=600,
        cmap='Reds',  # Blue color scheme for density
        colorbar=True,  # Show colorbar for density
        gridsize=20,    # Number of hexagons per axis
        tooltips=[('Count', '@c')],  # Show count of points in each bin
    )
    return heatmap

heatmap_dashboard = pn.Column(
    '# Net Income vs Dividend Payout Heatmap',
    create_netincome_dividend_heatmap(),
    sizing_mode='stretch_width'
)

# 7. Combined Layout with Tabs
full_dashboard = pn.Tabs(
    ('Financial Overview', original_dashboard),
    ('Key Metrics', new_dashboard),
    ('Heatmap Analysis', heatmap_dashboard),
    tabs_location='left'
)

# 8. Serve the Dashboard
full_dashboard.show()