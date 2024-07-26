#!/usr/bin/env python3

import numpy as np
import pandas as pd
import chardet
import datetime
from datetime import timedelta
import os
import tkinter as tk
from tkinter import filedialog, messagebox

def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
    return result['encoding']

def load_data(file_path, encoding):
    return pd.read_csv(file_path, encoding=encoding)

def remove_test_entries(df):
    substrings_to_remove = ['test', 'graham long', 'lizzie new', 'tahnee love']
    mask = ~df['Filed As'].str.lower().str.contains('|'.join(substrings_to_remove), case=False)
    return df[mask]

def remove_consultants(df):
    consultants_to_remove = ['Leiara Ferrett', 'Ebony Kouka', 'Alexandra Graham', 'Lisa Greaves', 'Elinor Faulkner']
    df = df[~df['Primary Consultant'].isin(consultants_to_remove)]
    df = df[df['Source'] != 'JB LinkedIn Connection']
    return df

def remove_invalid_emails(df):
    condition = (df['Primary Email'].str.endswith('@wave.com.au')) & (~df['Primary Email'].isin(['unknown@wave.com.au', 'tbc@wave.com.au']))
    df = df[~condition]
    df = df.drop('Primary Email', axis=1)
    return df

def remove_imported_status(df):
    mask = ~((df['Status'] == 'Imported') & (df['Source'].isin(['Headhunt', 'Linkedin'])))
    return df[mask]

def calculate_week_sunday_end(date):
    year, week, _ = date.isocalendar()
    return year, week

def add_week_number(df):
    # Specify the date format and ensure dayfirst is True if needed
    df['CreatedOn'] = pd.to_datetime(df['CreatedOn'], format='%d/%m/%Y %H:%M', dayfirst=True)
    df['Week'] = df['CreatedOn'].apply(lambda x: calculate_week_sunday_end(x)[1])
    return df

# Updated category list with consistent hyphen usage
categories = [
    "Allied Health", "Anaesthetics", "Divergent Careers", "Emergency Medicine", "General Manager", 
    "General Practice", "GP AMS", "GP Emergency", "GP Obstetrics", "GP Sexual Health", "GP Occ Health",
    "GP Skin", "GP Surgery", "GP Telehealth", "GP Urgent Care", "Intensive Care", 
    "Medical Administration", "Medicine - Cardiology", "Medicine - Dermatology", "Medicine - Diabetes",
    "Medicine - Gastroenterology", "Medicine - General", "Medicine - Geriatric", "Medicine - Occupational Health", 
    "Medicine - Haematology", "Medicine - Hepatology", "Medicine - Infectious Dis", "Medicine - Transfusion Medicine",
    "Medicine - Nephrology", "Medicine - Neurology", "Medicine - Occupational Health", "Medicine - Oncology", "Medicine - Immunology",
    "Medicine - Palliative Care", "Medicine - Rehabilitation", "Medicine - Respiratory", "Medicine - Pain",
    "Medicine - Rheumatology", "Medicine - Sports", "Medicine - Stroke", 
    "Nuclear Medicine", "Obstetrics & Gynaecology", "Other", "Paeds", 
    "Path", "Psych", "Public Health", "Radiation - Oncology", 
    "Radiology", "Surgery", "Unknown"
]
categories.sort(key=len, reverse=True)

def normalize_text(text):
    """ Normalize special characters in the text. """
    return text.replace('–', '-')

def match_category(specialty, categories):
    specialty = normalize_text(specialty)  # Normalize special characters
    for category in categories:
        if category in specialty:
            return category
    return 'Other'

def process_specialty(specialty):
    if pd.isna(specialty):
        return 'Unknown'
    
    specialty = normalize_text(specialty)  # Normalize special characters
    parts = specialty.split(',')
    first_arg = parts[0].strip()
    
    if (first_arg.startswith('Unknown') or first_arg.startswith('Other')) and len(parts) > 1:
        second_arg = parts[1].strip()
        return match_category(second_arg, categories)
    
    return match_category(first_arg, categories)

def add_specialty_category(df):
    df['Processed_Specialty'] = df['Specialty'].apply(process_specialty)
    return df

# Create a dictionary to map 'Primary Consultant' to 'Team Allocated'
team_mapping = {
    'Tahnee Love': 'JLD',
    'Craig Picard': 'JLD',
    'Ben Chegwidden': 'JLD',
    'Fiona Jackson': 'JLD',
    'Aimee Skoyles': 'JLD',
    'Mikaila Brooks': 'JLD',
    'Robyn Pascoe': 'Psych',
    'Courtney Lewis': 'Psych',
    'Yasmin Lockey': 'Psych',
    'Caitlin Lingard': 'HS Perm',
    'Jennifer Salinas': 'HS Perm',
    'Ashlea Harvey': 'HS Perm',
    'Chloe Frost': 'HS Perm',
    'EJ Cuaresma': 'GP Perm',
    'Jane Stanke': 'GP Perm',
    'Amber Derby-Davies': 'HS Locum',
    'Jade Camilleri': 'HS Locum',
    'Claudine Zaarour': 'HS Locum',
    'Hannah Kearns': 'HS Locum',
    'Eamon McCurry': 'HS Locum',
    'Nicole Langan': 'HS Locum',
    'Amy Beddall': 'GP Locum',
    'Cory Robertson': 'GP Locum',
    'Charlotte Hellmundt': 'GP Locum',
    'Anna Mullins': 'GP Locum',
    'Jade-Maree Camilleri': 'HS Locum',
    'Xanthia Gardner': 'HS Perm',
    'Charlie Hellmundt': 'GP Locum',
    'Paul Campbell': 'GP Locum',
    'Sharlina Drutschmann': 'GP Locum',
}

def assign_team_allocated(df):
    # Create the 'Team Allocated' column based on 'Primary Consultant' using the mapping dictionary
    df['Team Allocated'] = df['Primary Consultant'].map(team_mapping)

    # Filter for unmapped rows (where 'Primary Consultant' is not null and 'Team Allocated' is missing)
    unmapped_rows = df[df['Primary Consultant'].notna() & df['Team Allocated'].isna()]

    # Get the unique values of 'Primary Consultant' for unmapped rows
    unique_primary_consultants = unmapped_rows['Primary Consultant'].unique()
    print("Unmapped Primary Consultants:", unique_primary_consultants)

    # Non-Australia - Assign 'HS Perm' or 'GP Perm' based on specified conditions
    non_australia = (df['Country'] != 'Australia')

    # Check if neither 'Specialty' nor 'Seniority' contains 'GP' related phrases
    hs_perm_conditions = (
        non_australia &
        ~(
            (df['Specialty'].str.contains('GP|General Practice|General Practitioner', case=False)) | 
            (df['Seniority'].str.contains('GP|General Practice|General Practitioner', case=False))
        )
    )

    # Update 'HS Perm' for null 'Team Allocated' where the conditions are met
    df.loc[hs_perm_conditions & df['Team Allocated'].isnull(), 'Team Allocated'] = 'HS Perm'

    # Check for 'GP Perm' based on the same conditions
    gp_perm_conditions = (
        non_australia &
        (
            (df['Specialty'].str.contains('GP|General Practice|General Practitioner', case=False)) | 
            (df['Seniority'].str.contains('GP|General Practice|General Practitioner', case=False))
        )
    )

    # Update 'GP Perm' for null 'Team Allocated' based on specified conditions
    df.loc[gp_perm_conditions & df['Team Allocated'].isnull(), 'Team Allocated'] = 'GP Perm'

    # Australia Perm
    employment_conditions = (
        (df['Country'] == 'Australia') &
        (df['Employment Preference Attributes'].notna()) &
        (~df['Employment Preference Attributes'].str.contains('Locum', case=False, na=False))
    )

    gp_perm_conditions = (
        employment_conditions &
        (
            (df['Specialty'].str.contains('GP|General Practice|General Practitioner', case=False, na=False)) | 
            (df['Seniority'].str.contains('GP|General Practice|General Practitioner', case=False, na=False))
        )
    )

    # Set 'GP Perm' for 'Team Allocated' based on conditions
    df.loc[gp_perm_conditions & df['Team Allocated'].isnull(), 'Team Allocated'] = 'GP Perm'

    # Set 'HS Perm' for remaining null 'Team Allocated' based on conditions
    df.loc[employment_conditions & df['Team Allocated'].isnull(), 'Team Allocated'] = 'HS Perm'

    # Psych
    psych_conditions = (
        (df['Country'] == 'Australia') &
        (df['Specialty'].str.startswith('Psych')) &
        (df['Team Allocated'].isnull())
    )

    # Set 'Psych' for 'Team Allocated' if conditions are met
    df.loc[psych_conditions, 'Team Allocated'] = 'Psych'

    # Junior
    jld_conditions = (
        df['Team Allocated'].isnull() &
        df['Seniority'].str.contains('resident|registrar|cmo / smo|intern|student', case=False)
    )

    # Set 'JLD' for 'Team Allocated' where conditions are met
    df.loc[jld_conditions, 'Team Allocated'] = 'JLD'

    # Australia Locum
    # Check if either 'Specialty' or 'Seniority' contains GP-related phrases
    gp_locum_conditions = (
        (df['Team Allocated'].isnull()) &
        (df['Specialty'].str.contains('GP|General Practitioner|General Practice', case=False) |
        df['Seniority'].str.contains('GP|General Practitioner|General Practice', case=False))
    )

    # Set 'GP Locum' for rows with null 'Team Allocated' based on the specified conditions
    df.loc[gp_locum_conditions, 'Team Allocated'] = 'GP Locum'

    # Set 'HS Locum' for the remaining null 'Team Allocated' rows that don't meet the GP conditions
    df.loc[df['Team Allocated'].isnull(), 'Team Allocated'] = 'HS Locum'

    # Divergent Careers / Executives
    # Condition to check Seniority and Country
    seniority_conditions = (
        (df['Seniority'].str.contains('Director|DMS|Health Executive|Divergent Careers|Allied Health|Medical Admin|Scientist', case=False, na=False)) &
        (df['Country'] == 'Australia')
    )

    # Update 'HS Perm' for the specified conditions
    df.loc[seniority_conditions, 'Team Allocated'] = 'HS Perm'

    # Check for the specified condition
    condition = (df['Seniority'].str.contains('Director|DMS|Health Executive|Divergent Careers|Allied Health|Medical Admin|Scientist', case=False, na=False))

    # Get value counts for 'Team Allocated' for rows that satisfy the condition
    team_allocated_counts = df.loc[condition, 'Team Allocated'].value_counts()
    print("Team Allocated Counts for Seniority Conditions:")
    print(team_allocated_counts)

    seniority_condition = df['Seniority'].str.contains('Director|DMS|Health Executive|Divergent Careers|Allied Health|Medical Admin|Scientist', case=False, na=False)
    gp_perm_condition = df['Team Allocated'] == 'GP Perm'

    filtered_df = df[seniority_condition & gp_perm_condition]

    # Display relevant columns
    print(filtered_df.head())

    return df

def save_cleaned_data(df, encoding):
    current_date = datetime.datetime.now()
    previous_sunday = current_date - timedelta(days=current_date.weekday() + 1)
    previous_sunday_str = previous_sunday.strftime("%d%m%Y")
    folder_name = 'cleaned_new_leads'
    
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    
    file_path = os.path.join(folder_name, f'newleads_cleaned_{previous_sunday_str}.csv')
    df.to_csv(file_path, index=False, encoding=encoding)
    return file_path

def process_file(file_path):
    encoding = detect_encoding(file_path)
    df = load_data(file_path, encoding)
    
    df = remove_test_entries(df)
    df = remove_consultants(df)
    df = remove_invalid_emails(df)
    df = remove_imported_status(df)
    df = add_week_number(df)
    df = add_specialty_category(df)
    df = assign_team_allocated(df)
    
    saved_file_path = save_cleaned_data(df, encoding)
    return saved_file_path

def select_file():
    file_path = filedialog.askopenfilename(
        filetypes=[("CSV files", "*.csv")],
        title="Select a CSV file"
    )
    if file_path:
        try:
            saved_file_path = process_file(file_path)
            messagebox.showinfo("Success", f"File saved as {saved_file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

def main():
    root = tk.Tk()
    root.title("New Leads Cleaner")

    tk.Label(root, text="New Leads Cleaner", font=("Helvetica", 16)).pack(pady=20)
    tk.Button(root, text="Select CSV File", command=select_file, font=("Helvetica", 14)).pack(pady=20)

    root.mainloop()

if __name__ == "__main__":
    main()
