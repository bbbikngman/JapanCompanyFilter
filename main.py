import sys
import os
import time
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout,
                             QLabel, QFileDialog, QMessageBox, QHBoxLayout,
                             QLineEdit, QGridLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import traceback
import urllib.parse


class CompanyScraperThread(QThread):
    log_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, driver):
        super().__init__()
        self.driver = driver
        self.company_names = set()
        self.current_page = 1

    def get_companies_from_current_page(self):
        time.sleep(2)
        company_elements = self.driver.find_elements(
            By.CSS_SELECTOR,
            ".MuiBox-root.css-vfzywm .MuiTypography-root.MuiTypography-subtitle2.css-k1ckjv"
        )

        new_companies = 0
        for element in company_elements:
            company_name = element.text.strip()
            if company_name and '株式会社' in company_name:
                normalized_name = company_name.replace(' ', '')
                if normalized_name not in self.company_names:
                    self.company_names.add(normalized_name)
                    new_companies += 1
                    self.log_signal.emit(f"新しい会社を発見: {normalized_name}")

        return new_companies

    def run(self):
        try:
            # 处理第一页
            new_companies = self.get_companies_from_current_page()
            self.log_signal.emit(
                f"第 {self.current_page} ページを読み取り完了。このページで {new_companies} 社の新しい会社を発見、"
                f"現在の総数は {len(self.company_names)} 社です。")

        except Exception as e:
            self.error_signal.emit(f"会社名の取得中にエラーが発生しました: {str(e)}\n{traceback.format_exc()}")


class CompanyFilterThread(QThread):
    log_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)

    def __init__(self, driver, company_list, openwork_min, engage_min):
        super().__init__()
        self.driver = driver
        self.company_list = company_list
        self.openwork_min = float(openwork_min)
        self.engage_min = float(engage_min)
        self.filtered_companies = []

        options = webdriver.ChromeOptions()
        options.add_argument('--ignore-ssl-errors=yes')
        options.add_argument('--ignore-certificate-errors')
        # Suppress logging
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        self.driver = webdriver.Chrome(options=options)

    def process_openwork_companies(self):
        """OpenWorkの評価をまとめて処理"""
        results = {}
        total = len(self.company_list)

        for i, company in enumerate(self.company_list, 1):
            try:
                self.log_signal.emit(f"OpenWork処理中: {company} ({i}/{total})")
                self.progress_signal.emit(i, total)

                encoded_name = urllib.parse.quote(company)
                self.driver.get(
                    f"https://www.vorkers.com/company_list?field=&pref=&src_str={encoded_name}&sort=1&ct=comlist")

                try:
                    score_element = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".totalEvaluation_item.fs-15.fw-b"))
                    )
                    score = float(score_element.text)
                    if score >= self.openwork_min:
                        results[company] = score
                        self.log_signal.emit(f"OpenWork基準クリア: {company} - {score}")
                        print(f"OpenWorkスコア: {company} - {score}点")
                    else:
                        print(f"OpenWorkスコア: {company} - {score}点 (基準未満)")
                except:
                    self.log_signal.emit(f"OpenWork評価なし: {company}")
                    print(f"OpenWork評価なし: {company}")
                    continue

            except Exception as e:
                self.log_signal.emit(f"OpenWork処理エラー: {company} - {str(e)}")
                print(f"OpenWork処理エラー: {company} - {str(e)}")
                continue

        return results

    def process_engage_companies(self, qualified_companies):
        """エンゲージの評価をまとめて処理"""
        final_results = []
        total = len(qualified_companies)

        for i, (company, openwork_score) in enumerate(qualified_companies.items(), 1):
            try:
                self.log_signal.emit(f"エンゲージ処理中: {company} ({i}/{total})")
                self.progress_signal.emit(i, total)

                encoded_name = urllib.parse.quote(company)
                self.driver.get(f"https://en-hyouban.com/search/?SearchWords={encoded_name}")

                try:
                    score_element = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".point.font-weight-bold"))
                    )
                    engage_score = float(score_element.text)
                    print(f"エンゲージスコア: {company} - OpenWork: {openwork_score}点, エンゲージ: {engage_score}点 (最小基準: {self.engage_min})")

                    if engage_score >= self.engage_min:
                        result = f"{company}, OpenWork点数 {openwork_score}, エンゲージ点数 {engage_score}"
                        final_results.append(result)
                        self.log_signal.emit(f"両方の基準をクリア: {result}")
                        print(f"✓ 基準クリア: {result}")
                    else:
                        print(f"✗ 基準未達: {company} - エンゲージスコアが基準未満 ({engage_score} < {self.engage_min})")
                except:
                    self.log_signal.emit(f"エンゲージ評価なし: {company}")
                    print(f"エンゲージ評価なし: {company}")
                    continue

            except Exception as e:
                self.log_signal.emit(f"エンゲージ処理エラー: {company} - {str(e)}")
                print(f"エンゲージ処理エラー: {company} - {str(e)}")
                continue

        return final_results

    def run(self):
        try:
            # OpenWorkで最初のフィルタリング
            self.log_signal.emit("OpenWorkでの評価を取得中...")
            qualified_companies = self.process_openwork_companies()

            if not qualified_companies:
                self.log_signal.emit("OpenWork基準を満たす会社が見つかりませんでした")
                return

            # エンゲージで二次フィルタリング
            self.log_signal.emit("エンゲージでの評価を取得中...")
            self.filtered_companies = self.process_engage_companies(qualified_companies)

        except Exception as e:
            self.error_signal.emit(f"フィルタリング中にエラーが発生しました: {str(e)}\n{traceback.format_exc()}")


class CompanyScraperApp(QWidget):
    def __init__(self):
        super().__init__()
        self.driver = None
        self.scraper_thread = None
        self.filter_thread = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('GREEN高評判会社フィルター OPENWORK+エンゲージ')
        self.setGeometry(300, 300, 600, 500)

        layout = QGridLayout()
        font = QFont()
        font.setPointSize(12)
        self.setFont(font)

        # Filter criteria inputs
        filter_layout = QHBoxLayout()

        self.openwork_label = QLabel('OpenWork点数：', self)
        self.openwork_input = QLineEdit(self)
        self.openwork_input.setPlaceholderText('3.0')

        self.engage_label = QLabel('エンゲージ点数：', self)
        self.engage_input = QLineEdit(self)
        self.engage_input.setPlaceholderText('3.0')

        filter_layout.addWidget(self.openwork_label)
        filter_layout.addWidget(self.openwork_input)
        filter_layout.addWidget(self.engage_label)
        filter_layout.addWidget(self.engage_input)

        layout.addLayout(filter_layout, 0, 0, 1, 2)

        # Buttons
        self.green_start_btn = QPushButton('Green 起動', self)
        self.filter_start_btn = QPushButton('フィルター起動', self)
        self.search_start_btn = QPushButton('検索開始', self)
        self.next_page_btn = QPushButton('次のページへ', self)
        self.save_and_exit_btn = QPushButton('終了して保存', self)

        buttons = [self.green_start_btn, self.filter_start_btn, self.search_start_btn,
                   self.next_page_btn, self.save_and_exit_btn]
        for i, btn in enumerate(buttons):
            btn.setFont(font)
            layout.addWidget(btn, i + 1, 0, 1, 2)
            if btn != self.green_start_btn and btn != self.filter_start_btn:
                btn.setVisible(False)

        self.green_start_btn.clicked.connect(self.start_green_japan)
        self.filter_start_btn.clicked.connect(self.start_filtering)
        self.search_start_btn.clicked.connect(self.start_scraping)
        self.next_page_btn.clicked.connect(self.go_to_next_page)
        self.save_and_exit_btn.clicked.connect(self.save_and_exit)

        # Log label
        self.log_label = QLabel('', self)
        self.log_label.setWordWrap(True)
        self.log_label.setFont(font)
        layout.addWidget(self.log_label, len(buttons) + 1, 0, 1, 2)

        self.setLayout(layout)

    def start_filtering(self):
        if not self.openwork_input.text() or not self.engage_input.text():
            QMessageBox.warning(self, '警告', '両方のフィルター基準を入力してください')
            return

        try:
            float(self.openwork_input.text())
            float(self.engage_input.text())
        except ValueError:
            QMessageBox.warning(self, '警告', '数値を入力してください')
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, '会社リストを選択', '', 'テキストファイル (*.txt)')

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                companies = [line.strip() for line in f if line.strip()]

            if not companies:
                QMessageBox.warning(self, '警告', 'ファイルに会社データがありません')
                return

            options = webdriver.ChromeOptions()
            options.add_argument('--ignore-ssl-errors=yes')
            options.add_argument('--ignore-certificate-errors')
            # Suppress logging
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            
            self.driver = webdriver.Chrome(options=options)
            self.filter_thread = CompanyFilterThread(
                self.driver,
                companies,
                self.openwork_input.text(),
                self.engage_input.text()
            )

            self.filter_thread.log_signal.connect(self.update_log)
            self.filter_thread.error_signal.connect(self.handle_error)
            self.filter_thread.progress_signal.connect(self.update_progress)
            self.filter_thread.finished.connect(lambda: self.save_filtered_results(file_path))

            self.filter_thread.start()
            self.filter_start_btn.setEnabled(False)

        except Exception as e:
            QMessageBox.critical(self, 'エラー', f'フィルタリング開始時にエラーが発生しました: {str(e)}')

    def update_progress(self, current, total):
        self.log_label.setText(f'進捗状況: {current}/{total} 完了')

    def save_filtered_results(self, original_file_path):
        if not self.filter_thread or not self.filter_thread.filtered_companies:
            QMessageBox.warning(self, '結果', '基準を満たす会社が見つかりませんでした')
            return

        base_name = os.path.splitext(original_file_path)[0]
        new_file_path = f"{base_name}_FilteredbyOpenworkAndEngage.txt"

        try:
            with open(new_file_path, 'w', encoding='utf-8') as f:
                f.write("=== フィルタリング結果 ===\n")
                f.write(f"フィルター基準: エンゲージ最小スコア {self.filter_thread.engage_min}\n")
                f.write("======================\n\n")
                for company in self.filter_thread.filtered_companies:
                    f.write(f"{company}\n")

            message = (
                f'フィルタリング完了！\n'
                f'結果は {new_file_path} に保存されました。\n'
                f'基準を満たした会社数: {len(self.filter_thread.filtered_companies)}'
            )
            print(message)  # Console logging
            QMessageBox.information(self, '完了', message)
        except Exception as e:
            QMessageBox.critical(self, 'エラー', f'結果の保存中にエラーが発生しました: {str(e)}')

        finally:
            if self.driver:
                self.driver.quit()
            self.filter_start_btn.setEnabled(True)

    def start_green_japan(self):
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--ignore-ssl-errors=yes')
            options.add_argument('--ignore-certificate-errors')
            # Suppress logging
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.get("https://www.green-japan.com/search")

            self.green_start_btn.setVisible(False)
            self.search_start_btn.setVisible(True)

            QMessageBox.information(self, '説明',
                                    '1. ブラウザで求人を検索してください\n'
                                    '2. フィルターや条件を設定してください\n'
                                    '3. 「検索」ボタンを押してください\n'
                                    '4. 準備ができたら、「検索開始」ボタンを押してください')

        except Exception as e:
            QMessageBox.critical(self, 'エラー', f'ブラウザの起動中にエラーが発生しました: {str(e)}')

    def start_scraping(self):
        self.search_start_btn.setVisible(False)
        self.next_page_btn.setVisible(True)
        self.save_and_exit_btn.setVisible(True)

        self.scraper_thread = CompanyScraperThread(self.driver)
        self.scraper_thread.log_signal.connect(self.update_log)
        self.scraper_thread.error_signal.connect(self.handle_error)
        self.scraper_thread.start()

    def update_log(self, message):
        self.log_label.setText(message)

    def go_to_next_page(self):
        try:
            # 获取当前页面的公司信息
            new_companies = self.scraper_thread.get_companies_from_current_page()

            # 更新当前页码
            self.scraper_thread.current_page += 1

            # 更新日志
            self.scraper_thread.log_signal.emit(
                f"第 {self.scraper_thread.current_page} ページを読み取り完了。このページで {new_companies} 社の新しい会社を発見、"
                f"現在の総数は {len(self.scraper_thread.company_names)} 社です。")

            # 更新按钮文本
            self.next_page_btn.setText(f'第 {self.scraper_thread.current_page + 1} ページに移動したらクリックしてください')

        except Exception as e:
            QMessageBox.critical(self, 'エラー', f'ページの読み取り中にエラーが発生しました: {str(e)}')

    def save_and_exit(self):
        if not self.scraper_thread or not self.scraper_thread.company_names:
            QMessageBox.warning(self, '警告', '保存する会社データがありません')
            return

        file_path, _ = QFileDialog.getSaveFileName(self,
                                                   '会社名を保存',
                                                   'company_names.txt',
                                                   'テキストファイル (*.txt)')

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for company in sorted(self.scraper_thread.company_names):
                        f.write(company + '\n')
                QMessageBox.information(self, '成功',
                    f'合計 {len(self.scraper_thread.company_names)} 社の会社名を {file_path} に保存しました')
                if self.driver:
                    self.driver.quit()
                self.close()
            except Exception as e:
                QMessageBox.critical(self, 'エラー', f'ファイルの保存中にエラーが発生しました: {str(e)}')

    def handle_error(self, error_message):
        QMessageBox.critical(self, 'エラー', error_message)
        self.green_start_btn.setVisible(True)
        self.search_start_btn.setVisible(False)
        self.next_page_btn.setVisible(False)
        self.save_and_exit_btn.setVisible(False)

        if self.driver:
            self.driver.quit()

    def closeEvent(self, event):
        if self.driver:
            self.driver.quit()
        event.accept()


def main():
    app = QApplication(sys.argv)
    ex = CompanyScraperApp()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()