#!/usr/bin/env python3
import os
import subprocess

def show_menu():
    print("\n" + "="*40)
    print("PDF to Speech - Mobile Launcher")
    print("="*40)
    print("1. Run PDF to Speech Converter")
    print("2. List PDF files")
    print("3. Install dependencies")
    print("4. Exit")
    print("="*40)

def install_deps():
    print("Installing dependencies...")
    subprocess.run(["pip", "install", "pdfminer.six", "pyttsx3"])
    print("Dependencies installed!")

def list_pdfs():
    pdf_files = [f for f in os.listdir('.') if f.endswith('.pdf')]
    if pdf_files:
        print("PDF files found:")
        for i, f in enumerate(pdf_files, 1):
            print(f"  {i}. {f}")
    else:
        print("No PDF files found in current directory.")

def main():
    while True:
        show_menu()
        choice = input("Select option (1-4): ")
        
        if choice == '1':
            os.system("python mobile_main.py")
        elif choice == '2':
            list_pdfs()
        elif choice == '3':
            install_deps()
        elif choice == '4':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
