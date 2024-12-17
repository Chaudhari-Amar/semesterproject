# !pip install streamlit requests prettytable pandas plotly matplotlib

import requests
import json
import pandas as pd
import prettytable
import matplotlib.pyplot as plt
import plotly.express as px
import streamlit as st

def main():
    st.title("BLS Labor Statistics Dashboard (All-in-One)")

    # ---------------------------
    # 1. Collect data from BLS API
    # ---------------------------
    st.write("## 1. Data Collection from BLS API")
    headers = {'Content-type': 'application/json'}
    payload = {
        "seriesid": ['CUUR0000SA0', 'SUUR0000SA0'],  # Example BLS Series IDs
        "startyear": "2011",
        "endyear": "2014"
    }
    data = json.dumps(payload)

    # Call BLS API
    response = requests.post('https://api.bls.gov/publicAPI/v2/timeseries/data/', data=data, headers=headers)
    json_data = response.json()

    # Check if the API call succeeded
    if json_data['status'] != 'REQUEST_SUCCEEDED':
        st.error(f"Error in BLS API response: {json_data.get('message','Unknown error')}")
        st.stop()

    # Parse the API response
    bls_list = []
    for series in json_data['Results']['series']:
        series_id = series['seriesID']
        x = prettytable.PrettyTable(["Series ID", "Year", "Period", "Value", "Footnotes"])
        for item in series['data']:
            year = item['year']
            period = item['period']
            value = item['value']
            footnote_texts = [foot['text'] for foot in item['footnotes'] if foot and 'text' in foot]
            footnotes = ', '.join(footnote_texts)
            # Only keep monthly data
            if "M01" <= period <= "M12":
                bls_list.append([series_id, year, period, value, footnotes])
                x.add_row([series_id, year, period, value, footnotes])

        # Save each series to a .txt (optional)
        with open(f"{series_id}.txt", 'w') as f:
            f.write(x.get_string())

    # Build DataFrame
    df = pd.DataFrame(bls_list, columns=["Series ID", "Year", "Period", "Value", "Footnotes"])

    # Save to CSV
    df.to_csv("bls_data.csv", index=False)
    st.write("Data successfully downloaded from BLS and saved to `bls_data.csv`. Preview:")
    st.dataframe(df.head())

    # ---------------------------
    # 2. Clean and transform data
    # ---------------------------
    st.write("## 2. Data Transformation")
    # Convert 'Period' (e.g. 'M08') to numeric month
    df['Month'] = df['Period'].str.replace('M','', regex=False).astype(int)
    # Convert 'Value' to float
    df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
    # Create a combined Year-Month column
    df['Year-Month'] = df['Year'].astype(str) + "-" + df['Month'].astype(str)
    # Drop columns not needed
    df.drop(columns=['Footnotes', 'Period'], inplace=True)
    # Sort for a nice time-based order
    df.sort_values(by=['Series ID','Year','Month'], ascending=[True,True,True], inplace=True)
    df.reset_index(drop=True, inplace=True)

    st.write("Transformed DataFrame:")
    st.dataframe(df.head())

    # ----------------------------
    # 3. Streamlit Dashboard Setup
    # ----------------------------
    st.sidebar.header("Filter Options")
    series_list = df['Series ID'].unique()
    selected_series = st.sidebar.selectbox("Select Series ID", series_list)

    filtered_data = df[df['Series ID'] == selected_series].copy()

    st.write(f"### Trends for Series: {selected_series}")

    # Matplotlib Plot
    fig, ax = plt.subplots()
    ax.plot(filtered_data['Year-Month'], filtered_data['Value'], marker='o')
    ax.set_title(f"{selected_series} over Time")
    ax.set_xticklabels(filtered_data['Year-Month'], rotation=45, ha='right')
    ax.set_ylabel("Value")
    st.pyplot(fig)

    # Key Metrics
    st.write("### Key Metrics")
    max_val = filtered_data['Value'].max()
    min_val = filtered_data['Value'].min()
    avg_val = filtered_data['Value'].mean()
    col1, col2, col3 = st.columns(3)
    col1.metric("Max Value", f"{max_val:.2f}")
    col2.metric("Min Value", f"{min_val:.2f}")
    col3.metric("Average Value", f"{avg_val:.2f}")

    # Rolling Average Setting
    st.sidebar.subheader("Rolling Average Settings")
    window_size = st.sidebar.slider("Select Rolling Window (months)", min_value=1, max_value=12, value=3)
    filtered_data['Rolling_Avg'] = filtered_data['Value'].rolling(window=window_size).mean()

    st.write(f"### {window_size}-Month Rolling Average for {selected_series}")
    fig2, ax2 = plt.subplots()
    ax2.plot(filtered_data['Year-Month'], filtered_data['Value'], label='Original Data', alpha=0.5)
    ax2.plot(filtered_data['Year-Month'], filtered_data['Rolling_Avg'], label=f'{window_size}-Month Rolling Avg', color='red')
    plt.xticks(rotation=45)
    ax2.set_ylabel("Value")
    ax2.legend()
    st.pyplot(fig2)

    # Optional: Interactive Plotly
    st.write("### Interactive Plotly Chart")
    fig3 = px.line(filtered_data, x='Year-Month', y='Value', title=f"Trends for Series: {selected_series}")
    st.plotly_chart(fig3)

    st.success("All steps completed!")

if __name__ == "__main__":
    main()
