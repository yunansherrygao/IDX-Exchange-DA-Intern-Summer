import pandas as pd
from pathlib import Path
from datetime import date


# Folder that contains the monthly MLS CSV files
data_folder = Path("/Users/yunangao/Desktop/IDX Exchange")

# Date range: January 2024 through the most recently completed calendar month
start_month = "202401"

today = date.today()
if today.month == 1:
    end_month = f"{today.year - 1}12"
else:
    end_month = f"{today.year}{today.month - 1:02d}"

save_output = False


# Build the list of required months
months = pd.period_range(start=start_month, end=end_month, freq="M").strftime("%Y%m")

sold_dfs = []
sold_files_used = []

for month in months:
    filled_file = data_folder / f"CRMLSSold{month}_filled.csv"
    normal_file = data_folder / f"CRMLSSold{month}.csv"

    # If a filled file exists, use it instead of the normal file for that month
    # This includes the filled data without double-counting the same month
    if filled_file.exists():
        file_path = filled_file
    else:
        file_path = normal_file

    if not file_path.exists():
        print(f"Missing sold file for {month}")
        continue

    sold_month = pd.read_csv(file_path, low_memory=False)
    print(f"Sold {file_path.name}: {len(sold_month):,} rows before concatenation")

    sold_dfs.append(sold_month)
    sold_files_used.append(file_path.name)

sold_rows_before_concat = sum(len(df) for df in sold_dfs)
sold = pd.concat(sold_dfs, ignore_index=True)
sold_rows_after_concat = len(sold)

print("\nSold files used:")
print(sold_files_used)
print(f"Sold total rows before concatenation: {sold_rows_before_concat:,}")
print(f"Sold rows after concatenation: {sold_rows_after_concat:,}")

# Drop extra columns from the filled sold files
sold.drop(columns=["lonfilled", "latfilled"], inplace=True, errors="ignore")

sold_rows_before_filter = len(sold)
sold = sold[sold["PropertyType"].astype(str).str.strip() == "Residential"].copy()
sold_rows_after_filter = len(sold)

print(f"Sold rows before Residential filter: {sold_rows_before_filter:,}")
print(f"Sold rows after Residential filter: {sold_rows_after_filter:,}")

listing_dfs = []
listing_files_used = []

for month in months:
    file_path = data_folder / f"CRMLSListing{month}.csv"

    if not file_path.exists():
        print(f"Missing listing file for {month}")
        continue

    listing_month = pd.read_csv(file_path, low_memory=False)
    print(f"Listing {file_path.name}: {len(listing_month):,} rows before concatenation")

    listing_dfs.append(listing_month)
    listing_files_used.append(file_path.name)

listing_rows_before_concat = sum(len(df) for df in listing_dfs)
listings = pd.concat(listing_dfs, ignore_index=True)
listing_rows_after_concat = len(listings)

print(f"Listing total rows before concatenation: {listing_rows_before_concat:,}")
print(f"Listing rows after concatenation: {listing_rows_after_concat:,}")

listing_rows_before_filter = len(listings)
listings = listings[
    listings["PropertyType"].astype(str).str.strip() == "Residential"
].copy()
listing_rows_after_filter = len(listings)

print(f"Listing rows before Residential filter: {listing_rows_before_filter:,}")
print(f"Listing rows after Residential filter: {listing_rows_after_filter:,}")


# Save final CSV outputs
sold_output = data_folder / f"Combined_Sold_Residential_{start_month}_{end_month}.csv"
listing_output = data_folder / f"Combined_Listings_Residential_{start_month}_{end_month}.csv"

if save_output:
    sold.to_csv(sold_output, index=False)
    listings.to_csv(listing_output, index=False)


print("\nFinal results:")
print(f"Number of sold files loaded: {len(sold_files_used)}")
print(f"Number of listing files loaded: {len(listing_files_used)}")
print(f"Final Residential sold rows: {len(sold):,}")
print(f"Final Residential listing rows: {len(listings):,}")

# Listing total rows before concatenation: 930,144
# Listing rows after concatenation: 930,144
# Listing rows before Residential filter: 930,144
# Listing rows after Residential filter: 591,869