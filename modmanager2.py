import sys
import os
import shutil
import json
import uuid
import subprocess
from collections import Counter
from PIL import Image
from PyQt6.QtCore import Qt, QSize, QTimer, QThreadPool, QRunnable, pyqtSignal, QObject
# 确保导入了 QIcon
from PyQt6.QtGui import QPixmap, QImage, QColor, QKeyEvent, QIcon 
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QTreeWidget, QTreeWidgetItem, 
                             QPushButton, QLabel, QFileDialog, QMessageBox, 
                             QHeaderView, QLineEdit, QAbstractItemView, QCheckBox, 
                             QStyledItemDelegate, QFrame, QInputDialog)

# 版本号更新为 3.7.11
VERSION = "3.7.11" 

CONFIG_FILE = "settings_v3.json"
LANG_DIR = "languages"
MAX_PREVIEW_SIZE = 585
HOVER_DELAY_MS = 500 

COL_CAT = 0      
COL_CHECK = 1    
COL_PREVIEW = 2  
COL_NAME = 3  
COL_ACTION = 4   

COLUMN_PROPORTIONS = [0.18, 0.05, 0.10, 0.47, 0.20]

class I18nManager:
    def __init__(self, default_lang="zh_CN"):
        self.current_lang = default_lang
        self.translations = {}
        self.default_en = {
            "window_title": "Snowbreak Mod Manager",
            "path_game_paks": "Game Paks Path",
            "path_mod_repo": "Mod Library Path",
            "not_set": "Not Set",
            "btn_open": "📂 Open",
            "btn_set_game": "Select Game",
            "btn_set_repo": "Select Library",
            "search_placeholder": "🔍 Search Mods... (Ctrl +/- to Zoom)",
            "btn_select_all": "Select All",
            "btn_deselect_all": "Deselect All",
            "btn_batch_enable": "Enable Selected",
            "btn_batch_disable": "Disable Selected",
            "btn_batch_move": "Move Selected",
            "btn_delete": "Delete",
            "btn_new_folder": "New Folder",
            "btn_refresh": "Refresh",
            "btn_lang_toggle": "中文",
            "conflict_warn": "⚠ {} Name Conflicts",
            "header_folder": "Category",
            "header_preview": "Preview",
            "header_name": "Mod Name",
            "header_action": "Status",
            "cat_uncategorized": "Uncategorized",
            "mod_enabled": "Enabled",
            "mod_disabled": "Disabled",
            "tip_select_path": "Please set paths first!",
            "confirm_delete": "Are you sure you want to delete the selected items?",
            "msg_rename_fail": "Rename Failed",
            "msg_op_fail": "Operation Failed",
            "dialog_move_title": "Move Mods",
            "dialog_move_label": "Destination Folder:",
            "new_folder_default": "New Folder"
        }
        self.default_zh = {
            "window_title": "尘白禁区模组管理器",
            "path_game_paks": "游戏 Pak 路径",
            "path_mod_repo": "模组库路径",
            "not_set": "未设置",
            "btn_open": "📂 打开",
            "btn_set_game": "选择游戏路径",
            "btn_set_repo": "选择库路径",
            "search_placeholder": "🔍 搜索模组... (Ctrl +/- 缩放)",
            "btn_select_all": "全选",
            "btn_deselect_all": "取消全选",
            "btn_batch_enable": "启用选中",
            "btn_batch_disable": "禁用选中",
            "btn_batch_move": "移动选中",
            "btn_delete": "删除",
            "btn_new_folder": "新建文件夹",
            "btn_refresh": "刷新",
            "btn_lang_toggle": "EN",
            "conflict_warn": "⚠ {} 处名称冲突",
            "header_folder": "分类",
            "header_preview": "预览",
            "header_name": "模组名称",
            "header_action": "状态",
            "cat_uncategorized": "未分类",
            "mod_enabled": "已启用",
            "mod_disabled": "已禁用",
            "tip_select_path": "请先设置路径！",
            "confirm_delete": "确定要删除选中的项目吗？",
            "msg_rename_fail": "重命名失败",
            "msg_op_fail": "操作失败",
            "dialog_move_title": "移动模组",
            "dialog_move_label": "目标文件夹:",
            "new_folder_default": "新建文件夹"
        }
        self._ensure_lang_environment()
        self.load_language(default_lang)

    def _ensure_lang_environment(self):
        if not os.path.exists(LANG_DIR):
            os.makedirs(LANG_DIR)
        for code, data in [("zh_CN", self.default_zh), ("en", self.default_en)]:
            f_path = os.path.join(LANG_DIR, f"{code}.json")
            if not os.path.exists(f_path):
                try:
                    with open(f_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
                except: pass

    def load_language(self, lang_code):
        self.current_lang = lang_code
        lang_file = os.path.join(LANG_DIR, f"{lang_code}.json")
        if os.path.exists(lang_file):
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    self.translations = json.load(f)
            except:
                self.translations = self.default_zh if lang_code == "zh_CN" else self.default_en
        else:
            self.translations = self.default_zh if lang_code == "zh_CN" else self.default_en

    def t(self, key, *args):
        fallback = self.default_zh if self.current_lang == "zh_CN" else self.default_en
        text = self.translations.get(key, fallback.get(key, key))
        if args: return text.format(*args)
        return text

STYLE_TEMPLATE = """
QMainWindow {{ background-color: #1A1A1A; }}
QTreeWidget {{ 
    background-color: #242424;
    border: none; 
    color: #EEE; 
    font-size: {font_size}px; 
    outline: none;
}}
QHeaderView::section {{ 
    background-color: #2D2D2D; 
    color: white;
    padding: 6px; 
    border: none;
    border-bottom: 1px solid #333;
    font-size: {font_size}px;
}}
QCheckBox {{ background: transparent; }}
QCheckBox::indicator {{
    width: {check_size}px;
    height: {check_size}px;
    border: 2px solid #555;
    border-radius: 4px;
}}
QCheckBox::indicator:checked {{
    background-color: #0078D4;
    border: 2px solid #0078D4;
}}
QTreeWidget::item {{ 
    padding: {padding}px;
    border-bottom: 1px solid #2D2D2D; 
    min-height: {item_height}px;
}}
QPushButton {{ 
    background-color: #3A3A3A;
    color: white; border-radius: 4px;
    padding: {btn_v_padding}px {btn_h_padding}px; 
    font-weight: bold;
    font-size: {font_size}px;
}}
QPushButton:hover {{ background-color: #4A4A4A; }}
#btn_delete {{ background-color: #7D0000; }}
#btn_delete:hover {{ background-color: #C5000A; }}
#PathBar {{ background-color: #242424; border-radius: 6px; padding: 10px; }}
#PathLabel {{ color: #AAA; font-size: {small_font}px; }}
QLineEdit {{ 
    padding: {btn_v_padding}px; 
    background-color: #2D2D2D; color: white; 
    border: 1px solid #444; border-radius: 5px;
    font-size: {font_size}px;
}}

/* 垂直滚动条美化 */
QScrollBar:vertical {{
    background: #1A1A1A;
    width: {scroll_width}px;
    margin: 0px 0px 0px 0px;
}}
QScrollBar::handle:vertical {{
    background: #4F4F4F;
    min-height: 30px;
    border-radius: {scroll_radius}px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background: #666666;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}
"""

class RenameDelegate(QStyledItemDelegate): 
    def createEditor(self, parent, option, index): 
        item = self.parent().itemFromIndex(index) 
        if not item: return None 
        col = index.column() 
        i18n = self.parent().window().i18n
        if not item.parent(): 
            cat_text = item.text(COL_CAT).replace("📂 ", "").strip() 
            if col == COL_CAT and cat_text != i18n.t("cat_uncategorized"): 
                editor = QLineEdit(parent) 
                QTimer.singleShot(0, editor.selectAll) 
                return editor 
        elif col == COL_NAME: 
            editor = QLineEdit(parent) 
            QTimer.singleShot(0, editor.selectAll) 
            return editor 
        return None 

def pil_to_qimage(pil_img):
    if pil_img.mode != "RGBA": pil_img = pil_img.convert("RGBA")
    data = pil_img.tobytes("raw", "RGBA")
    return QImage(data, pil_img.size[0], pil_img.size[1], QImage.Format.Format_RGBA8888).copy()

class ImageLoadWorker(QRunnable):
    def __init__(self, path, raw_name, tid, callback_signal):
        super().__init__()
        self.path, self.raw_name, self.tid, self.callback_signal = path, raw_name, tid, callback_signal
    def run(self):
        try:
            if os.path.exists(self.path):
                with Image.open(self.path) as pil:
                    pil.load()
                    full_qimg = pil_to_qimage(pil)
                    thumb_pil = pil.copy()
                    thumb_pil.thumbnail((60, 60), Image.Resampling.LANCZOS)
                    self.callback_signal.emit(self.raw_name, pil_to_qimage(thumb_pil), full_qimg, self.tid, "")
            else: self.callback_signal.emit(self.raw_name, QImage(), QImage(), self.tid, "")
        except: self.callback_signal.emit(self.raw_name, QImage(), QImage(), self.tid, "")

class ImageLoadSignals(QObject):
    image_loaded = pyqtSignal(str, QImage, QImage, str, str)

class DropLabel(QLabel):
    def __init__(self, pak_name, rel_dir, parent_mgr):
        super().__init__("...")
        self.pak_name, self.rel_dir, self.mgr = pak_name, rel_dir, parent_mgr
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background: #2d2d2d; border-radius: 5px; color: #777; border: 1px dashed #444;")
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(lambda: self.mgr.show_large_preview(self.pak_name, self.mapToGlobal(self.rect().topRight())))
    def enterEvent(self, event): self.hover_timer.start(HOVER_DELAY_MS)
    def leaveEvent(self, event): 
        self.hover_timer.stop()
        self.mgr.preview_win.hide()
    def dragEnterEvent(self, event): 
        if event.mimeData().hasUrls(): event.acceptProposedAction()
    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls: self.mgr.handle_img_drop(self.pak_name, self.rel_dir, urls[0].toLocalFile())

class ModManager3(QMainWindow):
    def __init__(self):
        super().__init__()
        self.repo_path, self.game_path = "", ""
        self.i18n = I18nManager("zh_CN")
        self.load_config()

        # --- 图标路径自动处理逻辑 ---
        if getattr(sys, 'frozen', False):
            # 如果是打包后的环境，路径在 sys._MEIPASS
            base_path = sys._MEIPASS
        else:
            # 如果是平时运行 py 环境，路径就是当前文件夹
            base_path = os.path.abspath(".")
        
        # 这一行必须和 if/else 对齐，确保无论哪种情况都能执行
        icon_path = os.path.join(base_path, "app.ico")
    
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.zoom_level = 1.0 
        self.base_font_size = 14
        self.setWindowTitle(f"{self.i18n.t('window_title')} {VERSION}")
        
        # 设置窗口图标（请确保运行目录下有 app.ico 文件）
        if os.path.exists("app.ico"):
            self.setWindowIcon(QIcon("app.ico"))
        
        self.resize(1200, 850)
        self.qimage_cache, self.selected_mods, self.known_mods = {}, set(), set()
        self.is_first_scan, self.all_mods_in_repo, self.is_all_selected = True, set(), False 
        self.thread_pool = QThreadPool()
        self.image_load_signals = ImageLoadSignals()
        self.image_load_signals.image_loaded.connect(self.on_img_loaded)
        self.preview_win = QWidget()
        self.preview_win.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.preview_win_lbl = QLabel(self.preview_win)
        self.item_map = {}
        
        self.init_ui()
        self.apply_zoom() 
        self.refresh_data()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        path_bar = QFrame()
        path_bar.setObjectName("PathBar")
        path_bar_layout = QGridLayout(path_bar)
        
        self.game_title_lbl = QLabel(self.i18n.t('path_game_paks') + ":")
        self.game_title_lbl.setObjectName("PathLabel")
        self.repo_title_lbl = QLabel(self.i18n.t('path_mod_repo') + ":")
        self.repo_title_lbl.setObjectName("PathLabel")
        
        self.game_path_lbl = QLabel()
        self.game_path_lbl.setObjectName("PathLabel")
        self.repo_path_lbl = QLabel()
        self.repo_path_lbl.setObjectName("PathLabel")
        
        self.game_open_btn = QPushButton(self.i18n.t("btn_open"))
        self.game_open_btn.clicked.connect(lambda: self.open_folder_explorer(self.game_path))
        self.repo_open_btn = QPushButton(self.i18n.t("btn_open"))
        self.repo_open_btn.clicked.connect(lambda: self.open_folder_explorer(self.repo_path))
        self.game_btn = QPushButton(self.i18n.t("btn_set_game"))
        self.game_btn.clicked.connect(self.select_game)
        self.repo_btn = QPushButton(self.i18n.t("btn_set_repo"))
        self.repo_btn.clicked.connect(self.select_repo)

        path_bar_layout.addWidget(self.game_title_lbl, 0, 0)
        path_bar_layout.addWidget(self.game_path_lbl, 0, 1)
        path_bar_layout.addWidget(self.game_open_btn, 0, 2)
        path_bar_layout.addWidget(self.game_btn, 0, 3)
        
        path_bar_layout.addWidget(self.repo_title_lbl, 1, 0)
        path_bar_layout.addWidget(self.repo_path_lbl, 1, 1)
        path_bar_layout.addWidget(self.repo_open_btn, 1, 2)
        path_bar_layout.addWidget(self.repo_btn, 1, 3)
        
        path_bar_layout.setColumnStretch(1, 1)
        layout.addWidget(path_bar)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(self.i18n.t("search_placeholder"))
        self.search_bar.textChanged.connect(self.filter_list)
        layout.addWidget(self.search_bar)

        batch_layout = QHBoxLayout()
        self.all_sel_btn = QPushButton(self.i18n.t("btn_select_all"))
        self.all_sel_btn.clicked.connect(self.toggle_all_selection)
        batch_layout.addWidget(self.all_sel_btn)
        
        self.btn_batch_en = QPushButton(self.i18n.t("btn_batch_enable"))
        self.btn_batch_en.clicked.connect(lambda: self.exec_batch(True))
        batch_layout.addWidget(self.btn_batch_en)
        
        self.btn_batch_dis = QPushButton(self.i18n.t("btn_batch_disable"))
        self.btn_batch_dis.clicked.connect(lambda: self.exec_batch(False))
        batch_layout.addWidget(self.btn_batch_dis)
        
        self.btn_batch_move = QPushButton(self.i18n.t("btn_batch_move"))
        self.btn_batch_move.clicked.connect(self.batch_move_mods)
        batch_layout.addWidget(self.btn_batch_move)
        
        self.btn_batch_del = QPushButton(self.i18n.t("btn_delete"))
        self.btn_batch_del.setObjectName("btn_delete")
        self.btn_batch_del.clicked.connect(self.batch_delete_logic)
        batch_layout.addWidget(self.btn_batch_del)
        batch_layout.addStretch()
        
        self.conflict_label = QLabel("")
        self.conflict_label.setStyleSheet("color: #FF4444; font-weight: bold; margin-right: 10px;")
        batch_layout.addWidget(self.conflict_label)
        
        self.btn_new = QPushButton(self.i18n.t("btn_new_folder"))
        self.btn_new.clicked.connect(self.create_folder)
        self.btn_new.setStyleSheet("background-color: #2E5A2E;")
        batch_layout.addWidget(self.btn_new)

        self.lang_btn = QPushButton(self.i18n.t("btn_lang_toggle"))
        self.lang_btn.clicked.connect(self.toggle_language)
        self.lang_btn.setStyleSheet("background-color: #444;")
        batch_layout.addWidget(self.lang_btn)
        
        self.btn_ref = QPushButton(self.i18n.t("btn_refresh"))
        self.btn_ref.clicked.connect(self.manual_refresh_action)
        batch_layout.addWidget(self.btn_ref)
        layout.addLayout(batch_layout)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(5)
        self.update_tree_headers()
        self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(0)
        self.tree.header().setStretchLastSection(True)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.tree.setItemDelegate(RenameDelegate(self.tree))
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.itemChanged.connect(self.on_item_data_changed)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tree.header().setSectionsMovable(False)
        self.tree.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.tree.header().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.tree)

    def update_tree_headers(self):
        self.tree.setHeaderLabels([
            self.i18n.t("header_folder"), "", self.i18n.t("header_preview"), 
            self.i18n.t("header_name"), self.i18n.t("header_action")
        ])

    def toggle_language(self):
        new_lang = "en" if self.i18n.current_lang == "zh_CN" else "zh_CN"
        self.i18n.load_language(new_lang)
        self.save_cfg()
        
        self.setWindowTitle(f"{self.i18n.t('window_title')} {VERSION}")
        self.game_title_lbl.setText(self.i18n.t('path_game_paks') + ":")
        self.repo_title_lbl.setText(self.i18n.t('path_mod_repo') + ":")
        self.game_open_btn.setText(self.i18n.t("btn_open"))
        self.repo_open_btn.setText(self.i18n.t("btn_open"))
        self.game_btn.setText(self.i18n.t("btn_set_game"))
        self.repo_btn.setText(self.i18n.t("btn_set_repo"))
        self.search_bar.setPlaceholderText(self.i18n.t("search_placeholder"))
        self.all_sel_btn.setText(self.i18n.t("btn_select_all" if not self.is_all_selected else "btn_deselect_all"))
        self.btn_batch_en.setText(self.i18n.t("btn_batch_enable"))
        self.btn_batch_dis.setText(self.i18n.t("btn_batch_disable"))
        self.btn_batch_move.setText(self.i18n.t("btn_batch_move"))
        self.btn_batch_del.setText(self.i18n.t("btn_delete"))
        self.btn_new.setText(self.i18n.t("btn_new_folder"))
        self.btn_ref.setText(self.i18n.t("btn_refresh"))
        self.lang_btn.setText(self.i18n.t("btn_lang_toggle"))
        
        self.apply_zoom()
        self.refresh_data()

    def open_folder_explorer(self, path):
        if not path or not os.path.exists(path): return
        if sys.platform == 'win32': os.startfile(os.path.normpath(path))
        else: subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', path])

    def manual_refresh_action(self):
        if hasattr(self, 'current_cats'):
            for cat, paks in self.current_cats.items():
                for pak in paks: self.known_mods.add(pak)
        self.refresh_data()

    def keyPressEvent(self, event: QKeyEvent):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Equal: self.change_zoom(0.1)
            elif event.key() == Qt.Key.Key_Minus: self.change_zoom(-0.1)
            elif event.key() == Qt.Key.Key_0: self.zoom_level = 1.0
            self.apply_zoom()
        super().keyPressEvent(event)

    def change_zoom(self, delta):
        new_zoom = self.zoom_level + delta
        if 0.5 <= new_zoom <= 2.5: 
            self.zoom_level = new_zoom
            self.apply_zoom()

    def apply_zoom(self):
        f = int(self.base_font_size * self.zoom_level)
        padding = int(2 * self.zoom_level)
        item_h = int(68 * self.zoom_level)
        btn_v_p = int(6 * self.zoom_level)
        btn_h_p = int(12 * self.zoom_level)
        check_s = int(18 * self.zoom_level)
        small_f = int(13 * self.zoom_level)
        scroll_w = int(12 * self.zoom_level)
        scroll_r = int(6 * self.zoom_level)
      
        new_qss = STYLE_TEMPLATE.format(
             font_size=f, padding=padding, item_height=item_h,
             btn_v_padding=btn_v_p, btn_h_padding=btn_h_p,
             check_size=check_s, small_font=small_f,
             scroll_width=scroll_w, scroll_radius=scroll_r
        )
        self.setStyleSheet(new_qss)
        
        base_title_w = 150 if self.i18n.current_lang == "en" else 115
        self.game_title_lbl.setFixedWidth(int(base_title_w * self.zoom_level))
        self.repo_title_lbl.setFixedWidth(int(base_title_w * self.zoom_level))
        
        min_btn_w = int(100 * self.zoom_level)
        for btn in [self.game_open_btn, self.repo_open_btn, self.game_btn, self.repo_btn]:
            btn.setMinimumWidth(min_btn_w)
            btn.setMaximumWidth(250) 
            
        self.refresh_data() 

    def wrap_center(self, widget, height=None):
        if height is None: height = int(66 * self.zoom_level)
        c = QWidget()
        c.setFixedHeight(height)
        l = QHBoxLayout(c)
        l.setContentsMargins(8, 0, 8, 0)
        l.setSpacing(0)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(widget)
        return c

    def refresh_data(self):
        scroll_pos = self.tree.verticalScrollBar().value()
        not_set_html = f'<span style="color: #FF4444;">{self.i18n.t("not_set")}</span>'
        self.game_path_lbl.setText(f"{self.game_path if self.game_path else not_set_html}")
        self.repo_path_lbl.setText(f"{self.repo_path if self.repo_path else not_set_html}")
        self.update_tree_headers()

        if not self.repo_path or not self.game_path: return
        
        expanded_map = {self.tree.topLevelItem(i).text(COL_CAT).replace("📂 ", "").strip(): self.tree.topLevelItem(i).isExpanded() 
                        for i in range(self.tree.topLevelItemCount())}
            
        self.tree.blockSignals(True)
        self.tree.clear()
        self.item_map.clear()
        self.all_mods_in_repo.clear()
        game_files = os.listdir(self.game_path) if os.path.exists(self.game_path) else []
        uncat_key = self.i18n.t("cat_uncategorized")
        self.current_cats = {uncat_key: []}
        
        if os.path.exists(self.repo_path):
            for e in os.scandir(self.repo_path):
                if e.is_file() and e.name.lower().endswith(".pak"): 
                    self.current_cats[uncat_key].append(e.name)
                    self.all_mods_in_repo.add((uncat_key, e.name))
                elif e.is_dir(): 
                    paks = [f for f in os.listdir(e.path) if f.lower().endswith(".pak")]
                    self.current_cats[e.name] = paks
                    for p in paks: self.all_mods_in_repo.add((e.name, p))
        
        if self.is_first_scan:
            for cat, paks in self.current_cats.items():
                for pak in paks: self.known_mods.add(pak)
            self.is_first_scan = False

        counts = self.get_pak_counts()
        conflict_groups = sum(1 for pak_name in counts if counts[pak_name] > 1)
        self.conflict_label.setText(self.i18n.t("conflict_warn", conflict_groups) if conflict_groups > 0 else "")
        
        row_h, thumb_s = int(68 * self.zoom_level), int(60 * self.zoom_level)
        for cat, paks in self.current_cats.items():
            parent = QTreeWidgetItem(self.tree)
            cat_display = f"📂 {cat}"
            parent.setText(COL_CAT, cat_display)
            parent.setData(COL_CAT, Qt.ItemDataRole.UserRole, cat_display)
            parent.setFlags(parent.flags() | Qt.ItemFlag.ItemIsEditable)
            parent.setSizeHint(0, QSize(0, int(34 * self.zoom_level)))
            cb = QCheckBox()
            cb.stateChanged.connect(lambda st, it=parent: self.on_folder_cb(it, st))
            self.tree.setItemWidget(parent, COL_CHECK, self.wrap_center(cb, height=int(34 * self.zoom_level)))
            parent.setExpanded(expanded_map.get(cat, True))
            
            for pak in sorted(paks):
                is_en = pak in game_files
                item = QTreeWidgetItem(parent)
                item.setText(COL_NAME, pak)
                item.setData(COL_NAME, Qt.ItemDataRole.UserRole, pak)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                if pak not in self.known_mods: item.setForeground(COL_NAME, QColor("#00A3FF"))
                elif counts[pak] > 1: item.setForeground(COL_NAME, QColor("#FF4444"))
                else: item.setForeground(COL_NAME, QColor("#FFFFFF"))

                m_cb = QCheckBox()
                m_cb.setChecked((cat, pak) in self.selected_mods)
                m_cb.stateChanged.connect(lambda st, c=cat, p=pak: self.on_mod_cb(c, p, st))
                self.tree.setItemWidget(item, COL_CHECK, self.wrap_center(m_cb, row_h))
                
                rel = "" if cat == uncat_key else cat
                lbl = DropLabel(pak, rel, self)
                lbl.setFixedSize(thumb_s, thumb_s)
                self.tree.setItemWidget(item, COL_PREVIEW, self.wrap_center(lbl, row_h))
                
                btn_txt = self.i18n.t("mod_enabled") if is_en else self.i18n.t("mod_disabled")
                btn = QPushButton(btn_txt)
                btn.setMinimumWidth(int(100 * self.zoom_level))
                btn.setStyleSheet("background-color: #0078D4;" if is_en else "background-color: #3A3A3A; color: #AAA;")
                btn.clicked.connect(lambda chk, s=os.path.join(self.repo_path, rel, pak), p=pak, en=is_en, b=btn: self.toggle_mod(s, p, en, b))
                self.tree.setItemWidget(item, COL_ACTION, self.wrap_center(btn, row_h))
                
                tid = str(uuid.uuid4())
                self.item_map[tid] = lbl
                img_path = os.path.join(self.repo_path, rel, pak.replace(".pak", ".png"))
                self.thread_pool.start(ImageLoadWorker(img_path, pak.replace(".pak", ""), tid, self.image_load_signals.image_loaded))
                
        self.tree.blockSignals(False)
        self.sync_all_sel_state()
        QTimer.singleShot(0, self.adjust_cols)
        QTimer.singleShot(10, lambda: self.tree.verticalScrollBar().setValue(scroll_pos))

    def toggle_all_selection(self):
        if not self.repo_path: return
        self.is_all_selected = not self.is_all_selected
        self.selected_mods.clear()
        if self.is_all_selected:
            for cat, paks in self.current_cats.items():
                for pak in paks: self.selected_mods.add((cat, pak))
        self.tree.blockSignals(True)
        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            p_cb_w = self.tree.itemWidget(parent, COL_CHECK)
            if p_cb_w: p_cb_w.findChild(QCheckBox).setChecked(self.is_all_selected)
            for j in range(parent.childCount()):
                child = parent.child(j)
                c_cb_w = self.tree.itemWidget(child, COL_CHECK)
                if c_cb_w: c_cb_w.findChild(QCheckBox).setChecked(self.is_all_selected)
        self.tree.blockSignals(False)
        self.update_all_sel_btn_style()

    def update_all_sel_btn_style(self):
        self.all_sel_btn.setText(self.i18n.t("btn_deselect_all" if self.is_all_selected else "btn_select_all"))
        self.all_sel_btn.setStyleSheet("background-color: #0078D4; color: white;" if self.is_all_selected else "")

    def on_folder_cb(self, it, st):
        self.tree.blockSignals(True)
        is_checked = (st == Qt.CheckState.Checked.value)
        cat_name = it.text(COL_CAT).replace("📂 ", "").strip()
        for i in range(it.childCount()):
            child = it.child(i)
            w = self.tree.itemWidget(child, COL_CHECK)
            pak_name = child.text(COL_NAME)
            if w: w.findChild(QCheckBox).setChecked(is_checked)
            if is_checked: self.selected_mods.add((cat_name, pak_name))
            else: self.selected_mods.discard((cat_name, pak_name))
        self.tree.blockSignals(False)
        self.sync_all_sel_state()

    def on_mod_cb(self, c, p, st):
        if st == Qt.CheckState.Checked.value: self.selected_mods.add((c, p))
        else: self.selected_mods.discard((c, p))
        self.sync_all_sel_state()

    def sync_all_sel_state(self):
        total = len(self.all_mods_in_repo)
        self.is_all_selected = (total > 0 and len(self.selected_mods) >= total)
        self.update_all_sel_btn_style()

    def on_item_clicked(self, item, col): 
        if not item.parent(): 
            item.setExpanded(not item.isExpanded())
            QTimer.singleShot(10, self.adjust_cols)

    def on_item_data_changed(self, item, column):
        new_val = item.text(column).strip()
        if not new_val: self.refresh_data(); return
        old_val = item.data(column, Qt.ItemDataRole.UserRole)
        if not old_val or old_val == new_val: return
        uncat_key = self.i18n.t("cat_uncategorized")
        try:
            if not item.parent() and column == COL_CAT:
                old_clean, new_clean = old_val.replace("📂 ", "").strip(), new_val.replace("📂 ", "").strip()
                if old_clean == uncat_key: return
                os.rename(os.path.join(self.repo_path, old_clean), os.path.join(self.repo_path, new_clean))
            elif item.parent() and column == COL_NAME:
                if not new_val.lower().endswith(".pak"): new_val += ".pak"
                cat = item.parent().text(COL_CAT).replace("📂 ", "").strip()
                rel = "" if cat == uncat_key else cat
                if self.game_path:
                    old_game_pak = os.path.join(self.game_path, old_val)
                    if os.path.exists(old_game_pak): os.remove(old_game_pak)
                os.rename(os.path.join(self.repo_path, rel, old_val), os.path.join(self.repo_path, rel, new_val))
                img_old = os.path.join(self.repo_path, rel, old_val.replace(".pak", ".png"))
                if os.path.exists(img_old): os.rename(img_old, os.path.join(self.repo_path, rel, new_val.replace(".pak", ".png")))
                self.known_mods.discard(old_val)
                self.known_mods.add(new_val)
            self.refresh_data()
        except Exception as e: 
            QMessageBox.warning(self, self.i18n.t("msg_rename_fail"), str(e))
            self.refresh_data()

    def batch_move_mods(self): 
        if not self.selected_mods: return
        cats = list(self.current_cats.keys()) 
        dest_cat, ok = QInputDialog.getItem(self, self.i18n.t("dialog_move_title"), self.i18n.t("dialog_move_label"), cats, 0, False) 
        if ok and dest_cat: 
            uncat_key = self.i18n.t("cat_uncategorized")
            for src_cat, pak in list(self.selected_mods): 
                if src_cat != dest_cat:
                    try:
                        old_p = os.path.join(self.repo_path, "" if src_cat == uncat_key else src_cat, pak) 
                        new_dir = os.path.join(self.repo_path, "" if dest_cat == uncat_key else dest_cat) 
                        if not os.path.exists(new_dir): os.makedirs(new_dir) 
                        os.rename(old_p, os.path.join(new_dir, pak)) 
                        if os.path.exists(old_p.replace(".pak", ".png")):
                            os.rename(old_p.replace(".pak", ".png"), os.path.join(new_dir, pak.replace(".pak", ".png"))) 
                    except: pass
            self.selected_mods.clear()
            self.refresh_data()

    def batch_delete_logic(self): 
        if not self.selected_mods and self.tree.topLevelItemCount() == 0: return
        selected_folders, uncat_key = [], self.i18n.t("cat_uncategorized")
        for i in range(self.tree.topLevelItemCount()):
            p_item = self.tree.topLevelItem(i)
            p_cb_w = self.tree.itemWidget(p_item, COL_CHECK)
            if p_cb_w and p_cb_w.findChild(QCheckBox).isChecked():
                folder_name = p_item.text(COL_CAT).replace("📂 ", "").strip()
                if folder_name != uncat_key: selected_folders.append(folder_name)
        if not self.selected_mods and not selected_folders: return
        if QMessageBox.question(self, "", self.i18n.t("confirm_delete")) != QMessageBox.StandardButton.Yes: return 
        for f in selected_folders:
            try: shutil.rmtree(os.path.join(self.repo_path, f))
            except: pass
        for cat, pak in list(self.selected_mods): 
            if cat in selected_folders: continue 
            target_path = os.path.join(self.repo_path, "" if cat == uncat_key else cat, pak) 
            try: 
                if os.path.exists(target_path): os.remove(target_path) 
                if os.path.exists(target_path.replace(".pak", ".png")): os.remove(target_path.replace(".pak", ".png"))
                self.known_mods.discard(pak)
            except: pass 
        self.selected_mods.clear()
        self.refresh_data()

    def create_folder(self):
        if not self.repo_path: return
        base_name = self.i18n.t("new_folder_default")
        target_path = os.path.join(self.repo_path, base_name)
        counter = 1
        while os.path.exists(target_path):
            counter += 1
            target_path = os.path.join(self.repo_path, f"{base_name} ({counter})")
        try: 
            os.makedirs(target_path)
            self.refresh_data()
        except: pass

    def exec_batch(self, en):
        if not self.selected_mods: return
        uncat_key = self.i18n.t("cat_uncategorized")
        for cat, pak in list(self.selected_mods):
            src = os.path.join(self.repo_path, "" if cat == uncat_key else cat, pak)
            if os.path.exists(src):
                target = os.path.join(self.game_path, pak)
                try:
                    if en: shutil.copy2(src, target)
                    elif os.path.exists(target): os.remove(target)
                    self.known_mods.add(pak)
                except: pass
        self.refresh_data()

    def show_large_preview(self, pak, pos):
        rn = pak.replace(".pak", "")
        if rn in self.qimage_cache:
            pix = QPixmap.fromImage(self.qimage_cache[rn]).scaled(MAX_PREVIEW_SIZE, MAX_PREVIEW_SIZE, Qt.AspectRatioMode.KeepAspectRatio)
            self.preview_win_lbl.setPixmap(pix)
            self.preview_win_lbl.adjustSize()
            self.preview_win.adjustSize()
            self.preview_win.move(pos.x()+20, pos.y()-20)
            self.preview_win.show()

    def on_img_loaded(self, n, thumb, full, tid, msg):
        if tid in self.item_map and not thumb.isNull(): 
            ts = int(60 * self.zoom_level)
            pix = QPixmap.fromImage(thumb).scaled(ts, ts, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.item_map[tid].setPixmap(pix)
            self.item_map[tid].setText("")
            self.qimage_cache[n] = full

    def handle_img_drop(self, pak, rel, src):
        try:
            with Image.open(src) as img: img.convert("RGB").save(os.path.join(self.repo_path, rel, pak.replace(".pak", ".png")), "PNG")
            self.known_mods.add(pak)
            QTimer.singleShot(100, self.refresh_data)
        except: pass

    def filter_list(self):
        t = self.search_bar.text().lower()
        for i in range(self.tree.topLevelItemCount()):
            p = self.tree.topLevelItem(i)
            v = 0
            for j in range(p.childCount()):
                match = t in p.child(j).text(COL_NAME).lower()
                p.child(j).setHidden(not match)
                if match: v += 1
            p.setHidden(v == 0 and t != "")

    def get_pak_counts(self):
        if not hasattr(self, 'current_cats'): return Counter()
        return Counter([pak for paks in self.current_cats.values() for pak in paks])

    def toggle_mod(self, src, pak, is_en, btn_widget):
        try:
            target = os.path.join(self.game_path, pak)
            if is_en: 
                if os.path.exists(target): os.remove(target)
                new_en = False
            else: 
                shutil.copy2(src, target)
                new_en = True
            self.known_mods.add(pak)
            btn_widget.setText(self.i18n.t("mod_enabled" if new_en else "mod_disabled")) 
            btn_widget.setStyleSheet("background-color: #0078D4;" if new_en else "background-color: #3A3A3A; color: #AAA;") 
            try: btn_widget.clicked.disconnect()
            except: pass
            btn_widget.clicked.connect(lambda chk=False, s=src, p=pak, en=new_en, b=btn_widget: self.toggle_mod(s, p, en, b)) 
            self.refresh_data()
        except Exception as e: 
            QMessageBox.warning(self, self.i18n.t("msg_op_fail"), str(e))

    def select_repo(self):
        p = QFileDialog.getExistingDirectory(self, self.i18n.t("btn_set_repo"))
        if p: 
            self.repo_path = p
            self.save_cfg()
            self.refresh_data()

    def select_game(self):
        p = QFileDialog.getExistingDirectory(self, self.i18n.t("btn_set_game"))
        if p: 
            self.game_path = p
            self.save_cfg()
            self.refresh_data()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                    self.repo_path, self.game_path = d.get("repo", ""), d.get("game", "")
                    self.i18n.load_language(d.get("lang", "zh_CN"))
            except: pass

    def save_cfg(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f: 
            json.dump({"repo": self.repo_path, "game": self.game_path, "lang": self.i18n.current_lang}, f)

    def showEvent(self, event): 
        super().showEvent(event)
        QTimer.singleShot(50, self.adjust_cols)
        
    def resizeEvent(self, e): 
        super().resizeEvent(e)
        QTimer.singleShot(10, self.adjust_cols)
  
    def adjust_cols(self):
        header = self.tree.header()
        sw = self.tree.verticalScrollBar().width() if self.tree.verticalScrollBar().isVisible() else 0
        tw = self.tree.width() - sw
        if tw > 100:
            header.setUpdatesEnabled(False)
            for i in range(4):
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                calc_w = int(tw * COLUMN_PROPORTIONS[i])
                if i == COL_CHECK:
                    calc_w = max(int(40 * self.zoom_level), calc_w)
                self.tree.setColumnWidth(i, calc_w)
            header.setSectionResizeMode(COL_ACTION, QHeaderView.ResizeMode.ResizeToContents)
            if header.sectionSize(COL_ACTION) < int(tw * COLUMN_PROPORTIONS[COL_ACTION]):
                header.setSectionResizeMode(COL_ACTION, QHeaderView.ResizeMode.Stretch)
            header.setUpdatesEnabled(True)

if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    win = ModManager3()
    win.show()
    sys.exit(app.exec())