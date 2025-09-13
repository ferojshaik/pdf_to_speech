"""
PDF to Speech Android App
"""
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW, CENTER
import os
import re
from pathlib import Path
import asyncio

# PDF processing
try:
    from pdfminer.high_level import extract_text
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

class PDFToSpeechApp(toga.App):
    def startup(self):
        """Construct and show the Toga application."""
        
        # Main window
        self.main_window = toga.MainWindow(title=self.name)
        
        # Create main box
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=10))
        
        # Title
        title_label = toga.Label(
            "PDF to Speech Converter",
            style=Pack(text_align=CENTER, font_size=20, padding_bottom=20)
        )
        main_box.add(title_label)
        
        # PDF selection
        pdf_box = toga.Box(style=Pack(direction=ROW, padding_bottom=10))
        pdf_box.add(toga.Label("Select PDF:", style=Pack(width=100)))
        
        self.pdf_label = toga.Label("No PDF selected", style=Pack(flex=1))
        pdf_box.add(self.pdf_label)
        
        pdf_button = toga.Button(
            "Choose PDF",
            on_press=self.select_pdf,
            style=Pack(padding_left=10)
        )
        pdf_box.add(pdf_button)
        main_box.add(pdf_box)
        
        # Voice settings
        voice_box = toga.Box(style=Pack(direction=ROW, padding_bottom=10))
        voice_box.add(toga.Label("Voice:", style=Pack(width=100)))
        
        self.voice_select = toga.Selection(
            items=["Default Voice"],
            style=Pack(flex=1)
        )
        voice_box.add(self.voice_select)
        main_box.add(voice_box)
        
        # Speed setting
        speed_box = toga.Box(style=Pack(direction=ROW, padding_bottom=10))
        speed_box.add(toga.Label("Speed:", style=Pack(width=100)))
        
        self.speed_input = toga.NumberInput(
            value=175,
            min_value=50,
            max_value=300,
            style=Pack(flex=1)
        )
        speed_box.add(self.speed_input)
        main_box.add(speed_box)
        
        # Convert button
        convert_button = toga.Button(
            "Convert PDF to Speech",
            on_press=self.convert_pdf,
            style=Pack(padding_top=20, padding_bottom=20)
        )
        main_box.add(convert_button)
        
        # Progress
        self.progress_label = toga.Label(
            "Ready to convert",
            style=Pack(text_align=CENTER, padding_bottom=10)
        )
        main_box.add(self.progress_label)
        
        # Output files
        self.output_list = toga.Box(style=Pack(direction=COLUMN))
        main_box.add(self.output_list)
        
        # Set the content
        self.main_window.content = main_box
        self.main_window.show()
        
        # Initialize
        self.pdf_path = None
        self.output_dir = Path.home() / "PDFtoSpeech"
        self.output_dir.mkdir(exist_ok=True)
    
    def select_pdf(self, widget):
        """Select PDF file"""
        try:
            # For now, we'll use a simple file dialog
            # In a real implementation, you'd use toga's file dialog
            self.pdf_path = Path("sample.pdf")  # Placeholder
            self.pdf_label.text = "sample.pdf"
        except Exception as e:
            self.main_window.info_dialog("Error", f"Could not select PDF: {e}")
    
    async def convert_pdf(self, widget):
        """Convert PDF to speech"""
        if not self.pdf_path:
            self.main_window.info_dialog("Error", "Please select a PDF file first")
            return
        
        if not PDF_AVAILABLE:
            self.main_window.info_dialog("Error", "PDF processing not available")
            return
        
        try:
            self.progress_label.text = "Converting PDF..."
            
            # Extract text from PDF
            pages = self.read_pdf_pages(self.pdf_path)
            if not pages:
                self.main_window.info_dialog("Error", "No text found in PDF")
                return
            
            # Convert each page
            for i, page_text in enumerate(pages):
                if not page_text.strip():
                    continue
                
                # Normalize text
                text = self.normalize_text(page_text)
                if not text:
                    continue
                
                # Save as text file for now (TTS would need platform-specific implementation)
                output_file = self.output_dir / f"page_{i+1:04d}.txt"
                output_file.write_text(text, encoding='utf-8')
                
                # Add to output list
                self.add_output_file(output_file)
                
                self.progress_label.text = f"Converted page {i+1}/{len(pages)}"
            
            self.progress_label.text = "Conversion complete!"
            self.main_window.info_dialog("Success", "PDF converted successfully!")
            
        except Exception as e:
            self.main_window.error_dialog("Error", f"Conversion failed: {e}")
    
    def read_pdf_pages(self, pdf_path: Path):
        """Extract text from PDF as list of pages"""
        try:
            full_text = extract_text(str(pdf_path)) or ""
            pages = full_text.split("\f")
            pages = [p for p in pages if p.strip() != ""]
            return pages
        except Exception as e:
            print(f"Failed to read PDF: {e}")
            return []
    
    def normalize_text(self, txt: str) -> str:
        """Clean up text formatting"""
        txt = txt.replace("\r", "\n")
        txt = re.sub(r"[ \t]+", " ", txt)
        txt = re.sub(r"\n{3,}", "\n\n", txt)
        txt = "\n".join(line.strip() for line in txt.splitlines())
        return txt.strip()
    
    def add_output_file(self, file_path: Path):
        """Add output file to the list"""
        file_button = toga.Button(
            file_path.name,
            on_press=lambda w: self.open_file(file_path),
            style=Pack(padding_bottom=5)
        )
        self.output_list.add(file_button)
    
    def open_file(self, file_path: Path):
        """Open file with default application"""
        try:
            os.startfile(str(file_path))  # Windows
        except:
            try:
                os.system(f"open {file_path}")  # macOS
            except:
                os.system(f"xdg-open {file_path}")  # Linux

def main():
    return PDFToSpeechApp('PDF to Speech', 'com.example.pdftospeech')

if __name__ == '__main__':
    app = main()
    app.main_loop()
