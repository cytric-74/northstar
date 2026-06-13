from data_quality import *

FILE_PATH = "../data/raw/sales_data.csv"

df = load_data(FILE_PATH)

report = generate_quality_report(df)

print("\nDATA QUALITY REPORT")
print("-"*50)

for key, value in report.items():
    print(key)
    print(value)
    print()