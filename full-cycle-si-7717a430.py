# full-cycle-si-7717a430.py
import streamlit as st
import pandas as pd

def load_data(filepath):
    return pd.read_csv(filepath)

def display_data(data):
    st.write(data)

def main():
    st.title("Data Explorer")
    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])
    if uploaded_file is not None:
        data = load_data(uploaded_file)
        display_data(data)

if __name__ == "__main__":
    main()
