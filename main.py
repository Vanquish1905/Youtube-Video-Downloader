import tkinter as tk
import customtkinter as ctk
from yt_dlp import YoutubeDL
import threading
import os
import sys

class VanquishDownloader(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Vanquish's Youtube Video Downloader")
        self.geometry("950x600")
        
        self.themes = {
            "Blue": {"main": "#1f538d", "hover": "#14375e", "bg": "#242424", "side": "#1a1a1a"},
            "Green": {"main": "#2b713e", "hover": "#1e4f2b", "bg": "#121a12", "side": "#0d140d"},
            "Red": {"main": "#9c2a2a", "hover": "#6e1e1e", "bg": "#1a1212", "side": "#140d0d"},
            "Purple": {"main": "#5e35b1", "hover": "#4527a0", "bg": "#16121a", "side": "#100d14"}
        }

        self.languages = {
            "English": {"url": "Paste YouTube Link:", "dl": "Download Video", "set": "Settings", "lang": "Language", "col": "Theme Color", "succ": "Download Successful!", "err": "Extraction Failed", "work": "Bypassing YouTube..."},
            "German": {"url": "Link einfügen:", "dl": "Herunterladen", "set": "Einstellungen", "lang": "Sprache", "col": "Themenfarbe", "succ": "Erfolg!", "err": "Fehler beim Extrahieren", "work": "Umgehe YouTube..."},
            "French": {"url": "Coller le lien:", "dl": "Télécharger", "set": "Paramètres", "lang": "Langue", "col": "Couleur du thème", "succ": "Succès!", "err": "Échec de l'extraction", "work": "Traitement..."},
            "Spanish": {"url": "Pegar enlace:", "dl": "Descargar", "set": "Ajustes", "lang": "Idioma", "col": "Color del tema", "succ": "¡Éxito!", "err": "Error de extracción", "work": "Procesando..."},
            "Italian": {"url": "Incolla link:", "dl": "Scarica", "set": "Impostazioni", "lang": "Lingua", "col": "Colore tema", "succ": "Completato!", "err": "Errore", "work": "In corso..."},
            "Portuguese": {"url": "Colar link:", "dl": "Baixar", "set": "Configurações", "lang": "Idioma", "col": "Cor do tema", "succ": "Concluído!", "err": "Erro", "work": "Processando..."},
            "Dutch": {"url": "Link plakken:", "dl": "Downloaden", "set": "Instellingen", "lang": "Taal", "col": "Themakleur", "succ": "Geslaagd!", "err": "Fout", "work": "Verwerken..."},
            "Russian": {"url": "Вставьте ссылку:", "dl": "Скачать", "set": "Настройки", "lang": "Язык", "col": "Цвет", "succ": "Успешно!", "err": "Ошибка", "work": "Обход..."},
            "Chinese": {"url": "粘贴链接:", "dl": "下载", "set": "设置", "lang": "语言", "col": "颜色", "succ": "成功！", "err": "提取失败", "work": "正在解析..."},
            "Japanese": {"url": "リンクを貼り付け:", "dl": "ダウンロード", "set": "設定", "lang": "言語", "col": "カラー", "succ": "成功！", "err": "エラー", "work": "解析中..."},
            "Korean": {"url": "링크 붙여넣기:", "dl": "다운로드", "set": "설정", "lang": "언어", "col": "색상", "succ": "성공!", "err": "오류", "work": "처리 중..."},
            "Arabic": {"url": "إلصق الرابط:", "dl": "تنزيل", "set": "الإعدادات", "lang": "اللغة", "col": "اللون", "succ": "تم!", "err": "فشل", "work": "جاري..."},
            "Turkish": {"url": "Linki Yapıştır:", "dl": "İndir", "set": "Ayarlar", "lang": "Dil", "col": "Renk", "succ": "Başarılı!", "err": "Hata", "work": "İşleniyor..."},
            "Polish": {"url": "Wklej link:", "dl": "Pobierz", "set": "Ustawienia", "lang": "Język", "col": "Kolor", "succ": "Sukces!", "err": "Błąd", "work": "Pobieranie..."},
            "Swedish": {"url": "Klistra in länk:", "dl": "Ladda ner", "set": "Inställningar", "lang": "Språk", "col": "Färg", "succ": "Klart!", "err": "Fel", "work": "Vänta..."},
            "Danish": {"url": "Indsæt link:", "dl": "Download", "set": "Indstillinger", "lang": "Sprog", "col": "Farve", "succ": "Succes!", "err": "Fejl", "work": "Behandler..."},
            "Finnish": {"url": "Liitä linkki:", "dl": "Lataa", "set": "Asetukset", "lang": "Kieli", "col": "Väri", "succ": "Valmis!", "err": "Virhe", "work": "Käsitellään..."},
            "Norwegian": {"url": "Lim inn lenke:", "dl": "Last ned", "set": "Innstillinger", "lang": "Språk", "col": "Farge", "succ": "Suksess!", "err": "Feil", "work": "Behandler..."},
            "Greek": {"url": "Επικόλληση:", "dl": "Λήψη", "set": "Ρυθμίσεις", "lang": "Γλώσσα", "col": "Χρώμα", "succ": "Επιτυχία!", "err": "Σφάλμα", "work": "Επεξεργασία..."},
            "Hindi": {"url": "लिंक पेस्ट करें:", "dl": "डाउनलोड करें", "set": "सेटिंग्स", "lang": "भाषा", "col": "रंग", "succ": "सफल!", "err": "त्रुटि", "work": "प्रगति..."}
        }
        
        self.current_lang = "English"
        ctk.set_appearance_mode("Dark")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo = ctk.CTkLabel(self.sidebar, text="VANQUISH'S\nVAULT", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo.pack(pady=40)

        self.btn_dl_view = ctk.CTkButton(self.sidebar, text="Downloader", command=self.show_main)
        self.btn_dl_view.pack(pady=10, padx=20)

        self.btn_settings_view = ctk.CTkButton(self.sidebar, text="Settings", command=self.show_settings)
        self.btn_settings_view.pack(pady=10, padx=20)

        self.watermark = ctk.CTkLabel(self.sidebar, text="made by Vanquish\nV1", font=ctk.CTkFont(size=11), text_color="gray")
        self.watermark.pack(side="bottom", pady=20)

        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=40, pady=40)

        self.url_label = ctk.CTkLabel(self.main_frame, text=self.languages[self.current_lang]["url"], font=ctk.CTkFont(size=16))
        self.url_label.pack(pady=(60, 10))

        self.url_entry = ctk.CTkEntry(self.main_frame, width=500, height=45)
        self.url_entry.pack(pady=10)

        self.dl_main_btn = ctk.CTkButton(self.main_frame, text=self.languages[self.current_lang]["dl"], height=45, font=ctk.CTkFont(weight="bold"), command=self.start_download_thread)
        self.dl_main_btn.pack(pady=25)

        self.status_label = ctk.CTkLabel(self.main_frame, text="", font=ctk.CTkFont(size=13))
        self.status_label.pack(pady=10)

        self.settings_frame = ctk.CTkFrame(self, fg_color="transparent")
        
        self.s_lang_label = ctk.CTkLabel(self.settings_frame, text="App Language", font=ctk.CTkFont(size=16))
        self.s_lang_label.pack(pady=(50, 10))
        self.lang_menu = ctk.CTkOptionMenu(self.settings_frame, values=list(self.languages.keys()), command=self.update_language)
        self.lang_menu.pack(pady=10)

        self.s_col_label = ctk.CTkLabel(self.settings_frame, text="Theme Color", font=ctk.CTkFont(size=16))
        self.s_col_label.pack(pady=(30, 10))
        self.color_menu = ctk.CTkOptionMenu(self.settings_frame, values=list(self.themes.keys()), command=self.update_colors)
        self.color_menu.pack(pady=10)

        self.update_colors("Blue")

    def show_main(self):
        self.settings_frame.grid_forget()
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=40, pady=40)

    def show_settings(self):
        self.main_frame.grid_forget()
        self.settings_frame.grid(row=0, column=1, sticky="nsew", padx=40, pady=40)

    def update_language(self, choice):
        self.current_lang = choice
        l = self.languages[choice]
        self.url_label.configure(text=l["url"])
        self.dl_main_btn.configure(text=l["dl"])
        self.btn_settings_view.configure(text=l["set"])
        self.s_lang_label.configure(text=l["lang"])
        self.s_col_label.configure(text=l["col"])

    def update_colors(self, color_name):
        c = self.themes[color_name]
        self.configure(fg_color=c["bg"])
        self.sidebar.configure(fg_color=c["side"])
        
        for b in [self.btn_dl_view, self.btn_settings_view, self.dl_main_btn]:
            b.configure(fg_color=c["main"], hover_color=c["hover"])
            
        for m in [self.lang_menu, self.color_menu]:
            m.configure(fg_color=c["main"], button_color=c["main"], button_hover_color=c["hover"])

    def start_download_thread(self):
        threading.Thread(target=self.download_logic, daemon=True).start()

    def download_logic(self):
        url = self.url_entry.get().strip()
        if not url: return
        self.dl_main_btn.configure(state="disabled")
        self.status_label.configure(text=self.languages[self.current_lang]["work"], text_color="#3399FF")
        
        ydl_opts = {
            'format': 'best',
            'outtmpl': os.path.join(os.path.expanduser("~"), "Downloads", "%(title)s.%(ext)s"),
            'nocheckcertificate': True,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 15,
            'extractor_args': {'youtube': {'player_client': ['android']}},
            'user_agent': 'Mozilla/5.0 (Linux; Android 10; SM-G960U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.181 Mobile Safari/537.36'
        }
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.status_label.configure(text=self.languages[self.current_lang]["succ"], text_color="#4CAF50")
        except Exception:
            self.status_label.configure(text=self.languages[self.current_lang]["err"], text_color="#F44336")
        
        self.dl_main_btn.configure(state="normal")

if __name__ == "__main__":
    app = VanquishDownloader()
    app.mainloop()