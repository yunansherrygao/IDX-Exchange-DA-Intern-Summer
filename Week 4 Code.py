import pandas as pd
from pathlib import Path
from datetime import date
import os

#Combine csvs
data_folder = Path("/Users/yunangao/Desktop/IDX Exchange")

save_outputs = os.getenv("SAVE_OUTPUTS", "true").lower() == "true"

start_month = "202401"

today = date.today()
if today.month == 1:
    most_recent_completed_month = f"{today.year - 1}12"
else:
    most_recent_completed_month = f"{today.year}{today.month - 1:02d}"

available_listing_months = []
for file_path in data_folder.glob("CRMLSListing*.csv"):
    month = file_path.stem.replace("CRMLSListing", "")
    if month.isdigit() and len(month) == 6:
        available_listing_months.append(month)

available_sold_months = []
for file_path in data_folder.glob("CRMLSSold*.csv"):
    month = file_path.stem.replace("CRMLSSold", "").replace("_filled", "")
    if month.isdigit() and len(month) == 6:
        available_sold_months.append(month)

latest_available_month = min(max(available_listing_months), max(available_sold_months))
end_month = min(most_recent_completed_month, latest_available_month)

print(f"Most recently completed calendar month: {most_recent_completed_month}")
print(f"Latest available MLS month: {latest_available_month}")
print(f"Using MLS date range: {start_month} to {end_month}")

months = pd.period_range(start=start_month, end=end_month, freq="M").strftime("%Y%m")


sold_dfs = []
sold_files_used = []

for month in months:
    filled_file = data_folder / f"CRMLSSold{month}_filled.csv"
    normal_file = data_folder / f"CRMLSSold{month}.csv"

    if filled_file.exists():
        file_path = filled_file
    else:
        file_path = normal_file

    if not file_path.exists():
        print(f"Missing sold file for {month}")
        continue

    sold_month = pd.read_csv(file_path, low_memory=False)

    sold_dfs.append(sold_month)
    sold_files_used.append(file_path.name)

sold = pd.concat(sold_dfs, ignore_index=True)
sold.drop(columns=["lonfilled", "latfilled"], inplace=True, errors="ignore")

print(f"\nSold files loaded: {len(sold_files_used)}")
print(f"Sold rows after concatenation: {len(sold):,}")

listing_dfs = []
listing_files_used = []

for month in months:
    file_path = data_folder / f"CRMLSListing{month}.csv"

    if not file_path.exists():
        print(f"Missing listing file for {month}")
        continue

    listing_month = pd.read_csv(file_path, low_memory=False)

    listing_dfs.append(listing_month)
    listing_files_used.append(file_path.name)

listings = pd.concat(listing_dfs, ignore_index=True)

print(f"\nListing files loaded: {len(listing_files_used)}")
print(f"Listing rows after concatenation: {len(listings):,}")

sold = sold[sold["PropertyType"].astype(str).str.strip() == "Residential"].copy()
listings = listings[
    listings["PropertyType"].astype(str).str.strip() == "Residential"
].copy()

print(f"\nResidential sold rows: {len(sold):,}")
print(f"Residential listing rows: {len(listings):,}")

# extract API
url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"
mortgage = pd.read_csv(url, parse_dates=["observation_date"])
mortgage.columns = ["date", "rate_30yr_fixed"]
mortgage["rate_30yr_fixed"] = pd.to_numeric(
    mortgage["rate_30yr_fixed"],
    errors="coerce",
)

print(f"FRED mortgage rows loaded: {len(mortgage):,}")

mortgage["year_month"] = mortgage["date"].dt.to_period("M")
mortgage_monthly = (
    mortgage
    .groupby("year_month")["rate_30yr_fixed"]
    .mean()
    .reset_index()
)

print(f"Monthly mortgage rate rows: {len(mortgage_monthly):,}")

sold["CloseDate"] = pd.to_datetime(sold["CloseDate"], errors="coerce")
sold["year_month"] = sold["CloseDate"].dt.to_period("M")

listings["ListingContractDate"] = pd.to_datetime(
    listings["ListingContractDate"],
    errors="coerce",
)
listings["year_month"] = listings["ListingContractDate"].dt.to_period("M")

sold_with_rates = sold.merge(mortgage_monthly, on="year_month", how="left")
listings_with_rates = listings.merge(mortgage_monthly, on="year_month", how="left")

# check if there's null values
sold_null_rates = sold_with_rates["rate_30yr_fixed"].isnull().sum()
listing_null_rates = listings_with_rates["rate_30yr_fixed"].isnull().sum()

print("\nMortgage rate null validation:")
print(f"Sold rows with null mortgage rate: {sold_null_rates:,}")
print(f"Listing rows with null mortgage rate: {listing_null_rates:,}")

if sold_null_rates == 0 and listing_null_rates == 0:
    print("Validation passed: no null mortgage rate values after merge.")
else:
    print("Validation warning: some rows did not match to a mortgage rate.")

print("\nSold with mortgage rates preview:")
print(
    sold_with_rates[
        ["CloseDate", "year_month", "ClosePrice", "rate_30yr_fixed"]
    ].head()
)

print("\nListings with mortgage rates preview:")
print(
    listings_with_rates[
        ["ListingContractDate", "year_month", "ListPrice", "rate_30yr_fixed"]
    ].head()
)

sold_output = data_folder / f"Sold_Residential_With_Mortgage_Rates_{start_month}_{end_month}.csv"
listing_output = data_folder / f"Listings_Residential_With_Mortgage_Rates_{start_month}_{end_month}.csv"

if save_outputs:
    sold_with_rates.to_csv(sold_output, index=False)
    listings_with_rates.to_csv(listing_output, index=False)
    print(f"\nSaved sold enriched dataset to: {sold_output}")
    print(f"Saved listing enriched dataset to: {listing_output}")


print("\nFinal results:")
print(f"Sold enriched rows: {len(sold_with_rates):,}")
print(f"Listing enriched rows: {len(listings_with_rates):,}")
print(f"Sold enriched columns: {sold_with_rates.shape[1]:,}")
print(f"Listing enriched columns: {listings_with_rates.shape[1]:,}")
