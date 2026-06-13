import pandas as pd
import numpy as np

def load_data(filepath):
    df = pd.read_csv(filepath)
    return df

def check_missing_values(df):

    missing = df.isnull().sum()

    return missing

def check_duplicates(df):

    duplicates = df.duplicated().sum()

    return duplicates

def validate_dates(df):

    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce"
    )

    invalid_dates = df["Date"].isnull().sum()

    return invalid_dates

def clean_data(df):

    # remove duplicates
    df = df.drop_duplicates()

    # fix dates
    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce"
    )

    # remove invalid dates
    df = df.dropna(subset=["Date"])

    df.to_csv(
    "../data/cleaned/clean_sales_data.csv",
    index=False
    )

    return df

def generate_quality_report(df):

    report = {}

    report["Total Rows"] = len(df)

    report["Missing Values"] = (
        df.isnull().sum().to_dict()
    )

    report["Duplicate Rows"] = (
        df.duplicated().sum()
    )

    report["Invalid Dates"] = (
        pd.to_datetime(
            df["Date"],
            errors="coerce"
        ).isnull().sum()
    )

    return report