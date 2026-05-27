import asyncio
import aiohttp
import re
import sys
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from collections import Counter
from datetime import datetime

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import pyqtgraph as pg


class CrawlerWorker(QObject):
    """Рабочий класс для асинхронного краулинга"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(dict)
    url_processed = pyqtSignal(str, int)
    error = pyqtSignal(str)

    def __init__(self, start_url, max_depth=3, max_pages=50):
        super().__init__()
        self.start_url = start_url
        self.domain = urlparse(start_url).netloc
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.visited = set()
        self.word_counter = Counter()
        self.pages_count = 0
        self.queue = asyncio.Queue()
        self.is_running = True

    def is_internal(self, url):
        parsed = urlparse(url)
        return parsed.netloc == '' or parsed.netloc == self.domain

    def extract_data_sync(self, html, base_url):
        """Синхронная функция парсинга (выполняется в отдельном потоке)"""
        soup = BeautifulSoup(html, 'lxml')

        # Удаляем лишний мусор
        for script in soup(["script", "style", "header", "footer", "nav", "aside", "noscript"]):
            script.decompose()

        text = soup.get_text(separator=' ')
        words = re.findall(r'[а-яА-ЯёЁa-zA-Z]{3,}', text.lower())

        stop_words = {
            'что', 'для', 'как', 'это', 'все', 'его', 'был', 'они', 'еще', 'под',
            'при', 'был', 'были', 'года', 'году', 'было', 'после', 'этого', 'который',
            'также', 'только', 'этом', 'того', 'будет', 'через', 'более', 'очень',
            'the', 'and', 'for', 'that', 'this', 'with', 'from', 'are', 'was',
            'have', 'not', 'but', 'has', 'had', 'been', 'can', 'did', 'или', 'из', 'на'
        }

        filtered_words = [w for w in words if w not in stop_words]

        # Извлекаем ссылки
        links = []
        for link in soup.find_all('a', href=True):
            full_url = urljoin(base_url, link['href']).split('#')[0].rstrip('/')
            if self.is_internal(full_url):
                links.append(full_url)

        return filtered_words, links

    async def fetch(self, session, url, depth):
        if url in self.visited or self.pages_count >= self.max_pages or not self.is_running:
            return

        self.visited.add(url)
        self.pages_count += 1

        self.url_processed.emit(url, self.pages_count)
        self.progress.emit(int((self.pages_count / self.max_pages) * 100))

        try:
            async with session.get(url, timeout=15) as response:
                if response.status != 200:
                    self.error.emit(f"Ошибка {response.status}: {url}")
                    return

                html = await response.text()

                # Запускаем тяжелый парсинг HTML в пуле потоков, чтобы не блокировать Event Loop
                words, links = await asyncio.to_thread(self.extract_data_sync, html, url)
                self.word_counter.update(words)

                if depth < self.max_depth:
                    for full_url in links:
                        if full_url not in self.visited:
                            await self.queue.put((full_url, depth + 1))

        except Exception as e:
            self.error.emit(f"Сбой загрузки {url}: {str(e)}")

    async def worker(self, session):
        while self.is_running:
            try:
                url, depth = await asyncio.wait_for(self.queue.get(), timeout=2.0)
                await self.fetch(session, url, depth)
                self.queue.task_done()
            except asyncio.TimeoutError:
                if self.queue.empty():
                    break
            except Exception as e:
                self.error.emit(f"Ошибка воркера: {e}")

    async def run(self):
        try:
            # Имитируем реальный браузер для защиты от блокировок
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            connector = aiohttp.TCPConnector(limit_per_host=10)
            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                await self.queue.put((self.start_url, 0))

                # Запускаем 10 конкурентных воркеров
                workers = [asyncio.create_task(self.worker(session)) for _ in range(10)]
                await self.queue.join()

                for w in workers:
                    w.cancel()
        except Exception as e:
            self.error.emit(f"Критическая ошибка краулера: {e}")

        self.finished.emit(dict(self.word_counter.most_common(50)))


class WebCrawlerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.crawler_worker = None
        self.crawler_thread = None
        self.init_ui()
        self.setup_modern_theme()

    def apply_shadow(self, widget):
        """Добавляет современную тень к виджету"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 80))
        widget.setGraphicsEffect(shadow)

    def init_ui(self):
        self.setWindowTitle("Nexus Crawler Pro")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(900, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # QSplitter позволяет изменять размер панелей перетаскиванием
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Левая панель
        left_panel = self.create_left_panel()
        self.apply_shadow(left_panel)
        splitter.addWidget(left_panel)

        # Правая панель
        right_panel = self.create_right_panel()
        self.apply_shadow(right_panel)
        splitter.addWidget(right_panel)

        # Пропорции сплиттера (1 к 2)
        splitter.setSizes([350, 800])

        # Статус бар
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("⚡ Система готова к работе")
        self.status_bar.addWidget(self.status_label)

    def create_left_panel(self):
        panel = QFrame()
        panel.setObjectName("ControlPanel")
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)

        title = QLabel("⚙️ Управление")
        title.setObjectName("HeaderTitle")
        layout.addWidget(title)

        # Настройки
        settings_layout = QVBoxLayout()

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        self.url_input.setText("https://python.org")
        settings_layout.addWidget(QLabel("Базовый URL:"))
        settings_layout.addWidget(self.url_input)

        h_params = QHBoxLayout()

        v_depth = QVBoxLayout()
        self.depth_spin = QSpinBox()
        self.depth_spin.setRange(1, 10)
        self.depth_spin.setValue(2)
        v_depth.addWidget(QLabel("Глубина:"))
        v_depth.addWidget(self.depth_spin)

        v_pages = QVBoxLayout()
        self.pages_spin = QSpinBox()
        self.pages_spin.setRange(10, 5000)
        self.pages_spin.setValue(100)
        self.pages_spin.setSingleStep(50)
        v_pages.addWidget(QLabel("Макс. страниц:"))
        v_pages.addWidget(self.pages_spin)

        h_params.addLayout(v_depth)
        h_params.addLayout(v_pages)
        settings_layout.addLayout(h_params)

        layout.addLayout(settings_layout)

        # Кнопки
        self.start_btn = QPushButton("▶ Запустить сканирование")
        self.start_btn.setObjectName("StartButton")
        self.start_btn.clicked.connect(self.start_crawling)

        self.stop_btn = QPushButton("⏹ Остановить")
        self.stop_btn.setObjectName("StopButton")
        self.stop_btn.clicked.connect(self.stop_crawling)
        self.stop_btn.setEnabled(False)

        self.export_btn = QPushButton("💾 Экспорт в CSV")
        self.export_btn.setObjectName("ExportButton")
        self.export_btn.clicked.connect(self.export_results)

        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.export_btn)

        # Прогресс
        layout.addWidget(QLabel("Прогресс выполнения:"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_bar)

        # Лог
        layout.addWidget(QLabel("Системный журнал:"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        return panel

    def create_right_panel(self):
        panel = QFrame()
        panel.setObjectName("DataPanel")
        layout = QVBoxLayout(panel)

        tabs = QTabWidget()

        # Таблица
        table_tab = QWidget()
        table_layout = QVBoxLayout(table_tab)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Ранг", "Ключевое слово", "Встречаемость"])
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table_layout.addWidget(self.results_table)

        self.stats_label = QLabel("Ожидание данных...")
        self.stats_label.setObjectName("StatsLabel")
        table_layout.addWidget(self.stats_label)
        tabs.addTab(table_tab, "📊 Анализ текста")

        # График (PyQtGraph)
        graph_tab = QWidget()
        graph_layout = QVBoxLayout(graph_tab)

        pg.setConfigOptions(antialias=True)
        self.graph_widget = pg.PlotWidget()
        self.graph_widget.setBackground('#1e1e1e')
        self.graph_widget.getAxis('left').setPen('#888888')
        self.graph_widget.getAxis('bottom').setPen('#888888')
        graph_layout.addWidget(self.graph_widget)
        tabs.addTab(graph_tab, "📈 Визуализация")

        # URL список
        urls_tab = QWidget()
        urls_layout = QVBoxLayout(urls_tab)
        self.urls_list = QListWidget()
        urls_layout.addWidget(self.urls_list)
        tabs.addTab(urls_tab, "🔗 Карта ссылок")

        layout.addWidget(tabs)
        return panel

    def setup_modern_theme(self):
        """Современная темная тема с акцентами"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            QFrame#ControlPanel, QFrame#DataPanel {
                background-color: #1e1e1e;
                border-radius: 12px;
                border: 1px solid #333333;
            }
            QLabel {
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            QLabel#HeaderTitle {
                font-size: 18px;
                font-weight: bold;
                color: #ffffff;
                margin-bottom: 10px;
            }
            QLabel#StatsLabel {
                color: #64b5f6;
                font-weight: bold;
                padding: 5px;
            }
            QLineEdit, QSpinBox {
                padding: 10px;
                background-color: #2c2c2c;
                border: 1px solid #444444;
                border-radius: 6px;
                color: #ffffff;
                font-size: 13px;
            }
            QLineEdit:focus, QSpinBox:focus {
                border: 1px solid #64b5f6;
                background-color: #333333;
            }
            QPushButton {
                padding: 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                color: white;
            }
            QPushButton#StartButton {
                background-color: #43a047;
                border: 1px solid #2e7d32;
            }
            QPushButton#StartButton:hover { background-color: #4caf50; }

            QPushButton#StopButton {
                background-color: #e53935;
                border: 1px solid #c62828;
            }
            QPushButton#StopButton:hover { background-color: #ef5350; }

            QPushButton#ExportButton {
                background-color: #1e88e5;
                border: 1px solid #1565c0;
            }
            QPushButton#ExportButton:hover { background-color: #42a5f5; }

            QPushButton:disabled {
                background-color: #424242;
                color: #757575;
                border: 1px solid #333333;
            }
            QProgressBar {
                background-color: #2c2c2c;
                border-radius: 6px;
                text-align: center;
                color: white;
                font-weight: bold;
                border: 1px solid #444444;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e88e5, stop:1 #64b5f6);
                border-radius: 5px;
            }
            QTextEdit, QListWidget, QTableWidget {
                background-color: #232323;
                border: 1px solid #333333;
                border-radius: 8px;
                color: #e0e0e0;
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #1565c0;
            }
            QHeaderView::section {
                background-color: #2c2c2c;
                color: #ffffff;
                padding: 5px;
                border: 1px solid #333333;
                font-weight: bold;
            }
            QTabWidget::pane {
                border: 1px solid #333333;
                border-radius: 6px;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background: #2c2c2c;
                color: #e0e0e0;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background: #1e88e5;
                color: white;
                font-weight: bold;
            }
            QScrollBar:vertical {
                border: none;
                background: #1e1e1e;
                width: 12px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover { background: #777777; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"<span style='color:#888888'>[{timestamp}]</span> {message}")
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def add_url_to_list(self, url, count):
        self.urls_list.addItem(f"[{count}] {url}")
        self.urls_list.scrollToBottom()

    def add_error(self, error):
        self.log_message(f"<span style='color:#ef5350'>✖ {error}</span>")

    def start_crawling(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Ошибка", "Укажите корректный URL")
            return

        # Сброс интерфейса
        self.results_table.setRowCount(0)
        self.urls_list.clear()
        self.log_text.clear()
        self.progress_bar.setValue(0)
        self.graph_widget.clear()

        # Состояния кнопок
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.url_input.setEnabled(False)
        self.depth_spin.setEnabled(False)
        self.pages_spin.setEnabled(False)

        self.log_message(f"<b style='color:#64b5f6'>▶ Запуск анализа:</b> {url}")
        self.status_label.setText("⚙️ Выполняется сканирование...")

        # Инициализация Worker'а
        self.crawler_worker = CrawlerWorker(
            url,
            max_depth=self.depth_spin.value(),
            max_pages=self.pages_spin.value()
        )

        self.crawler_thread = QThread()
        self.crawler_worker.moveToThread(self.crawler_thread)

        # Коннекты
        self.crawler_worker.progress.connect(self.update_progress)
        self.crawler_worker.status.connect(self.log_message)
        self.crawler_worker.url_processed.connect(self.add_url_to_list)
        self.crawler_worker.error.connect(self.add_error)
        self.crawler_worker.finished.connect(self.on_crawling_finished)

        # Безопасный запуск асинхронной петли внутри QThread
        self.crawler_thread.started.connect(
            lambda: asyncio.run(self.crawler_worker.run())
        )
        self.crawler_thread.start()

    def stop_crawling(self):
        if self.crawler_worker:
            self.crawler_worker.is_running = False
        self.log_message("<b style='color:#ffb74d'>⏹ Остановка процесса...</b>")
        self.stop_btn.setEnabled(False)
        self.status_label.setText("🛑 Остановлено пользователем")

    def on_crawling_finished(self, results):
        self.log_message("<b style='color:#81c784'>✅ Операция завершена</b>")
        self.status_label.setText("✅ Сканирование успешно завершено")

        # Обновление таблицы
        self.results_table.setRowCount(min(50, len(results)))
        for i, (word, count) in enumerate(sorted(results.items(), key=lambda x: x[1], reverse=True)[:50]):
            rank_item = QTableWidgetItem(f"#{i + 1}")
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            word_item = QTableWidgetItem(word)

            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.results_table.setItem(i, 0, rank_item)
            self.results_table.setItem(i, 1, word_item)
            self.results_table.setItem(i, 2, count_item)

        self.stats_label.setText(
            f"🔗 Просканировано: {self.crawler_worker.pages_count} стр. | "
            f"📝 Уникальных токенов: {len(results)}"
        )

        self.update_graph(results)
        self.reset_ui()

    def update_graph(self, results):
        self.graph_widget.clear()
        top_words = sorted(results.items(), key=lambda x: x[1], reverse=True)[:15]

        if top_words:
            x = list(range(len(top_words)))
            y = [count for _, count in top_words]
            ticks = [word for word, _ in top_words]

            # Современные столбцы с неоновым оттенком
            bg = pg.BarGraphItem(x=x, height=y, width=0.7, brush='#64b5f6', pen='#1565c0')
            self.graph_widget.addItem(bg)

            ax = self.graph_widget.getAxis('bottom')
            ax.setTicks([list(zip(x, ticks))])

    def export_results(self):
        if self.results_table.rowCount() == 0:
            QMessageBox.warning(self, "Внимание", "Нет данных для сохранения.")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчет", "crawler_report.csv", "CSV Files (*.csv)"
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("Rank,Keyword,Frequency\n")
                    for row in range(self.results_table.rowCount()):
                        rank = self.results_table.item(row, 0).text().replace('#', '')
                        word = self.results_table.item(row, 1).text()
                        count = self.results_table.item(row, 2).text()
                        f.write(f"{rank},{word},{count}\n")

                self.log_message(f"💾 Данные успешно экспортированы в {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Сбой записи файла:\n{e}")

    def reset_ui(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.url_input.setEnabled(True)
        self.depth_spin.setEnabled(True)
        self.pages_spin.setEnabled(True)
        if self.crawler_thread:
            self.crawler_thread.quit()
            self.crawler_thread.wait()

    def closeEvent(self, event):
        if self.crawler_worker and self.crawler_worker.is_running:
            self.crawler_worker.is_running = False
        if self.crawler_thread and self.crawler_thread.isRunning():
            self.crawler_thread.quit()
            self.crawler_thread.wait()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Обязательно для правильного применения QSS тем
    window = WebCrawlerGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()