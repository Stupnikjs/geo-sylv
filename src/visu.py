import argparse
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px

def process_and_visualize(csv_path):
    print(f"Loading data from: {csv_path} ...")
    
    # 1. Load the data
    try:
        # Use sep='|' and skipinitialspace=True to handle the formatting
        df = pd.read_csv(csv_path, skipinitialspace=True)
        df = df.dropna() # Remove empty lines
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        return

    # 2. Clean and prepare data
    # Convert date to datetime objects
    df['date'] = pd.to_datetime(df['date'])

    # Remove anomalous NDMI values (1.0 and -1.0 are usually mask errors)
    df = df[(df['mean'] > -0.99) & (df['mean'] < 0.99)]

    # Group by date to average the two overlapping tiles (T31UGP and T32ULU)
    daily_df = df.groupby('date').agg({
        'mean': 'mean',
        'std': 'mean',
        'p10': 'mean',
        'valid_fraction': 'mean'
    }).reset_index()

    # Extract Year and Month for seasonal analysis
    daily_df['year'] = daily_df['date'].dt.year
    daily_df['month'] = daily_df['date'].dt.strftime('%b') # e.g., 'Jan', 'Feb'

    # --- VISUALIZATION 1: Static Time Series with Variability ---
    print("Generating static time series plot...")
    plt.figure(figsize=(14, 6))

    # Plot the mean NDMI line
    plt.plot(daily_df['date'], daily_df['mean'], color='blue', label='Mean NDMI', linewidth=1.5)

    # Add a shaded area for standard deviation (variability across the region)
    plt.fill_between(daily_df['date'], 
                     daily_df['mean'] - daily_df['std'], 
                     daily_df['mean'] + daily_df['std'], 
                     color='blue', alpha=0.2, label='Spatial Variability (± 1 Std Dev)')

    plt.title('NDMI Time Series in Vosges (2017 - 2023)', fontsize=16)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('NDMI Value', fontsize=12)
    plt.axhline(0, color='black', linewidth=0.8, linestyle='--') # Zero line
    plt.legend()
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    
    # Save the static plot to a file and display it
    static_plot_path = "ndmi_timeseries.png"
    plt.savefig(static_plot_path, dpi=300)
    print(f"Static plot saved to: {static_plot_path}")
    plt.show()

    # --- VISUALIZATION 2: Interactive Seasonal Plot (Plotly) ---
    print("Generating interactive seasonal plot...")
    fig = px.line(daily_df, x='month', y='mean', color='year', 
                  markers=True, line_group='year',
                  title='Seasonal NDMI Trends by Year (2017-2023)',
                  labels={'mean': 'Mean NDMI', 'month': 'Month'},
                  category_orders={'month': ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']})

    fig.update_layout(hovermode='x unified')
    
    # This will open the interactive plot in your default web browser
    fig.show()
    print("Done!")

if __name__ == "__main__":
    # Set up the argument parser
    parser = argparse.ArgumentParser(description="Visualize NDMI time-series data from a CSV file.")
    
    # Add the argument for the CSV file path
    parser.add_argument(
        "csv_path", 
        type=str, 
        help="Path to the input CSV file (e.g., ndmi_vosges_2017_2023.csv)"
    )
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Run the visualization function with the provided path
    process_and_visualize(args.csv_path)