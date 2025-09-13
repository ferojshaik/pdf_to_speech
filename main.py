# main.py - Kivy Android App for PDF to Speech
import os
import json
import logging
import re
import time
from pathlib import Path
from typing import List
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from kivy.utils import platform
from kivy.core.audio import SoundLoader
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout

# Android-specific imports
if platform == 'android':
    from android.permissions import request_permissions, Permission
    from android.storage import primary_external_storage_path
    from jnius import autoclass
    from android import activity
    
    # Android TTS
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
    Locale = autoclass('java.util.Locale')
    File = autoclass('java.io.File')
    Environment = autoclass('android.os.Environment')
    
    # Request permissions
    request_permissions([
        Permission.READ_EXTERNAL_STORAGE,
        Permission.WRITE_EXTERNAL_STORAGE,
        Permission.INTERNET
    ])

# PDF processing
try:
    from pdfminer.high_level import extract_text
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# TTS for non-Android platforms
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

# Logging
logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("pdf_tts_app")

class PDFToSpeechApp(App):
    def build(self):
        self.title = "PDF to Speech Converter"
        self.pdf_path = None
        self.output_dir = None
        self.tts_engine = None
        self.voices = []
        self.current_voice = 0
        self.speech_rate = 175
        self.volume = 1.0
        
        # Set up output directory
        if platform == 'android':
            self.output_dir = Path(primary_external_storage_path()) / "PDFtoSpeech"
        else:
            self.output_dir = Path.home() / "PDFtoSpeech"
        
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize TTS
        self.init_tts()
        
        # Create main layout
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Title
        title = Label(text="PDF to Speech Converter", size_hint_y=None, height=50, font_size=24)
        main_layout.add_widget(title)
        
        # PDF selection
        pdf_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        pdf_layout.add_widget(Label(text="Select PDF:", size_hint_x=0.3))
        self.pdf_label = Label(text="No PDF selected", size_hint_x=0.7)
        pdf_layout.add_widget(self.pdf_label)
        main_layout.add_widget(pdf_layout)
        
        # File chooser button
        file_btn = Button(text="Choose PDF File", size_hint_y=None, height=50)
        file_btn.bind(on_press=self.show_file_chooser)
        main_layout.add_widget(file_btn)
        
        # Voice selection
        voice_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        voice_layout.add_widget(Label(text="Voice:", size_hint_x=0.3))
        self.voice_spinner = Spinner(text="Default", size_hint_x=0.7)
        self.voice_spinner.bind(text=self.on_voice_change)
        voice_layout.add_widget(self.voice_spinner)
        main_layout.add_widget(voice_layout)
        
        # Speech rate
        rate_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        rate_layout.add_widget(Label(text="Speed:", size_hint_x=0.3))
        self.rate_slider = Slider(min=50, max=300, value=175, size_hint_x=0.7)
        self.rate_slider.bind(value=self.on_rate_change)
        rate_layout.add_widget(self.rate_slider)
        self.rate_label = Label(text="175 WPM", size_hint_x=0.2)
        rate_layout.add_widget(self.rate_label)
        main_layout.add_widget(rate_layout)
        
        # Volume
        volume_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        volume_layout.add_widget(Label(text="Volume:", size_hint_x=0.3))
        self.volume_slider = Slider(min=0, max=1, value=1, size_hint_x=0.7)
        self.volume_slider.bind(value=self.on_volume_change)
        volume_layout.add_widget(self.volume_slider)
        self.volume_label = Label(text="100%", size_hint_x=0.2)
        volume_layout.add_widget(self.volume_label)
        main_layout.add_widget(volume_layout)
        
        # Progress
        self.progress_label = Label(text="Ready to convert", size_hint_y=None, height=30)
        main_layout.add_widget(self.progress_label)
        
        self.progress_bar = ProgressBar(max=100, size_hint_y=None, height=30)
        main_layout.add_widget(self.progress_bar)
        
        # Convert button
        convert_btn = Button(text="Convert PDF to Speech", size_hint_y=None, height=60, font_size=18)
        convert_btn.bind(on_press=self.convert_pdf)
        main_layout.add_widget(convert_btn)
        
        # Output files list
        output_label = Label(text="Output Files:", size_hint_y=None, height=30)
        main_layout.add_widget(output_label)
        
        # Scrollable output list
        scroll = ScrollView()
        self.output_list = GridLayout(cols=1, size_hint_y=None, spacing=5)
        self.output_list.bind(minimum_height=self.output_list.setter('height'))
        scroll.add_widget(self.output_list)
        main_layout.add_widget(scroll)
        
        return main_layout
    
    def init_tts(self):
        """Initialize TTS engine based on platform"""
        if platform == 'android':
            self.init_android_tts()
        elif PYTTSX3_AVAILABLE:
            self.init_pyttsx3_tts()
        else:
            self.show_error("TTS not available on this platform")
    
    def init_android_tts(self):
        """Initialize Android TTS"""
        try:
            self.tts_engine = TextToSpeech(PythonActivity.mActivity, None)
            self.tts_engine.setLanguage(Locale.US)
            self.load_android_voices()
        except Exception as e:
            LOG.error(f"Failed to initialize Android TTS: {e}")
            self.show_error("Failed to initialize TTS")
    
    def init_pyttsx3_tts(self):
        """Initialize pyttsx3 TTS"""
        try:
            self.tts_engine = pyttsx3.init()
            self.load_pyttsx3_voices()
        except Exception as e:
            LOG.error(f"Failed to initialize pyttsx3 TTS: {e}")
            self.show_error("Failed to initialize TTS")
    
    def load_android_voices(self):
        """Load available Android voices"""
        self.voices = ["Default"]
        self.voice_spinner.values = self.voices
    
    def load_pyttsx3_voices(self):
        """Load available pyttsx3 voices"""
        try:
            voices = self.tts_engine.getProperty('voices')
            self.voices = ["Default"]
            for i, voice in enumerate(voices):
                name = getattr(voice, 'name', f'Voice {i}')
                self.voices.append(name)
            self.voice_spinner.values = self.voices
        except Exception as e:
            LOG.error(f"Failed to load voices: {e}")
            self.voices = ["Default"]
            self.voice_spinner.values = self.voices
    
    def on_voice_change(self, spinner, text):
        """Handle voice selection change"""
        if platform == 'android' and self.tts_engine:
            # Android voice selection would go here
            pass
        elif PYTTSX3_AVAILABLE and self.tts_engine:
            try:
                voices = self.tts_engine.getProperty('voices')
                if text != "Default" and voices:
                    voice_index = self.voices.index(text) - 1
                    if 0 <= voice_index < len(voices):
                        self.tts_engine.setProperty('voice', voices[voice_index].id)
            except Exception as e:
                LOG.error(f"Failed to set voice: {e}")
    
    def on_rate_change(self, slider, value):
        """Handle speech rate change"""
        self.speech_rate = int(value)
        self.rate_label.text = f"{self.speech_rate} WPM"
        
        if platform == 'android' and self.tts_engine:
            # Convert WPM to Android rate (0.1 to 2.0)
            android_rate = max(0.1, min(2.0, value / 100.0))
            self.tts_engine.setSpeechRate(android_rate)
        elif PYTTSX3_AVAILABLE and self.tts_engine:
            self.tts_engine.setProperty('rate', self.speech_rate)
    
    def on_volume_change(self, slider, value):
        """Handle volume change"""
        self.volume = value
        self.volume_label.text = f"{int(value * 100)}%"
        
        if platform == 'android' and self.tts_engine:
            self.tts_engine.setPitch(1.0)  # Android doesn't have direct volume control
        elif PYTTSX3_AVAILABLE and self.tts_engine:
            self.tts_engine.setProperty('volume', self.volume)
    
    def show_file_chooser(self, instance):
        """Show file chooser popup"""
        content = BoxLayout(orientation='vertical', spacing=10)
        
        file_chooser = FileChooserListView(
            path=str(Path.home()),
            filters=['*.pdf']
        )
        content.add_widget(file_chooser)
        
        btn_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        select_btn = Button(text='Select')
        cancel_btn = Button(text='Cancel')
        
        btn_layout.add_widget(select_btn)
        btn_layout.add_widget(cancel_btn)
        content.add_widget(btn_layout)
        
        popup = Popup(title='Choose PDF File', content=content, size_hint=(0.9, 0.9))
        
        def select_file(instance):
            if file_chooser.selection:
                self.pdf_path = Path(file_chooser.selection[0])
                self.pdf_label.text = self.pdf_path.name
            popup.dismiss()
        
        def cancel(instance):
            popup.dismiss()
        
        select_btn.bind(on_press=select_file)
        cancel_btn.bind(on_press=cancel)
        popup.open()
    
    def convert_pdf(self, instance):
        """Convert PDF to speech"""
        if not self.pdf_path or not self.pdf_path.exists():
            self.show_error("Please select a valid PDF file")
            return
        
        if not PDF_AVAILABLE:
            self.show_error("PDF processing not available. Please install pdfminer.six")
            return
        
        if not self.tts_engine:
            self.show_error("TTS engine not available")
            return
        
        # Start conversion in a separate thread
        Clock.schedule_once(lambda dt: self.start_conversion(), 0.1)
    
    def start_conversion(self):
        """Start the PDF conversion process"""
        try:
            self.progress_label.text = "Extracting text from PDF..."
            self.progress_bar.value = 0
            
            # Extract text from PDF
            pages = self.read_pdf_pages(self.pdf_path)
            if not pages:
                self.show_error("No text found in PDF")
                return
            
            total_pages = len(pages)
            self.progress_label.text = f"Converting {total_pages} pages..."
            
            # Convert each page
            for i, page_text in enumerate(pages):
                if not page_text.strip():
                    continue
                
                # Normalize text
                text = self.normalize_text(page_text)
                if not text:
                    continue
                
                # Split into chunks
                chunks = self.split_into_chunks(text)
                
                # Generate audio for each chunk
                for j, chunk in enumerate(chunks):
                    output_file = self.output_dir / f"page_{i+1:04d}_chunk_{j+1:02d}.wav"
                    self.text_to_speech_file(chunk, output_file)
                
                # Update progress
                progress = ((i + 1) / total_pages) * 100
                self.progress_bar.value = progress
                self.progress_label.text = f"Converting page {i+1}/{total_pages}"
                
                # Add output file to list
                self.add_output_file(output_file)
            
            self.progress_label.text = "Conversion complete!"
            self.progress_bar.value = 100
            
        except Exception as e:
            LOG.error(f"Conversion failed: {e}")
            self.show_error(f"Conversion failed: {str(e)}")
    
    def read_pdf_pages(self, pdf_path: Path) -> List[str]:
        """Extract text from PDF as list of pages"""
        try:
            full_text = extract_text(str(pdf_path)) or ""
            pages = full_text.split("\f")
            pages = [p for p in pages if p.strip() != ""]
            return pages
        except Exception as e:
            LOG.error(f"Failed to read PDF: {e}")
            return []
    
    def normalize_text(self, txt: str) -> str:
        """Clean up text formatting"""
        txt = txt.replace("\r", "\n")
        txt = re.sub(r"[ \t]+", " ", txt)
        txt = re.sub(r"\n{3,}", "\n\n", txt)
        txt = "\n".join(line.strip() for line in txt.splitlines())
        return txt.strip()
    
    def split_into_chunks(self, text: str, max_chars: int = 1500) -> List[str]:
        """Split text into TTS-friendly chunks"""
        text = text.strip()
        if not text:
            return []
        
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks = []
        buf = []
        
        def flush_buf():
            if buf:
                chunks.append(" ".join(buf).strip())
                buf.clear()
        
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            
            if len(s) > max_chars:
                start = 0
                while start < len(s):
                    end = min(start + max_chars, len(s))
                    chunks.append(s[start:end])
                    start = end
                continue
            
            tentative = (" ".join(buf + [s])).strip()
            if len(tentative) <= max_chars:
                buf.append(s)
            else:
                flush_buf()
                buf.append(s)
        
        flush_buf()
        return [c for c in chunks if c.strip()]
    
    def text_to_speech_file(self, text: str, output_path: Path):
        """Convert text to speech and save to file"""
        try:
            if platform == 'android':
                self.android_tts_to_file(text, output_path)
            elif PYTTSX3_AVAILABLE:
                self.pyttsx3_tts_to_file(text, output_path)
        except Exception as e:
            LOG.error(f"TTS conversion failed: {e}")
    
    def android_tts_to_file(self, text: str, output_path: Path):
        """Android TTS to file (simplified - would need more complex implementation)"""
        # This is a simplified version - in practice, you'd need to use
        # Android's TTS synthesis to file functionality
        LOG.info(f"Android TTS: {text[:50]}...")
        # For now, create a placeholder file
        output_path.write_text("Audio placeholder")
    
    def pyttsx3_tts_to_file(self, text: str, output_path: Path):
        """pyttsx3 TTS to file"""
        try:
            self.tts_engine.save_to_file(text, str(output_path))
            self.tts_engine.runAndWait()
        except Exception as e:
            LOG.error(f"pyttsx3 TTS failed: {e}")
    
    def add_output_file(self, file_path: Path):
        """Add output file to the list"""
        btn = Button(
            text=file_path.name,
            size_hint_y=None,
            height=40
        )
        btn.bind(on_press=lambda x: self.play_audio(file_path))
        self.output_list.add_widget(btn)
    
    def play_audio(self, file_path: Path):
        """Play audio file"""
        try:
            if file_path.exists():
                sound = SoundLoader.load(str(file_path))
                if sound:
                    sound.play()
        except Exception as e:
            LOG.error(f"Failed to play audio: {e}")
    
    def show_error(self, message: str):
        """Show error popup"""
        content = BoxLayout(orientation='vertical', spacing=10)
        content.add_widget(Label(text=message))
        close_btn = Button(text='Close', size_hint_y=None, height=50)
        content.add_widget(close_btn)
        
        popup = Popup(title='Error', content=content, size_hint=(0.8, 0.4))
        close_btn.bind(on_press=popup.dismiss)
        popup.open()

if __name__ == '__main__':
    PDFToSpeechApp().run()
