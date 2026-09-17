"""
ویجت درخت شایستگی - نمایش ساختار سه‌لایه
Competency (شایستگی) → Indicator (شاخص) → ObservableBehavior (رفتار قابل مشاهده)
با قابلیت انتخاب و بازگشت مقدار
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
    QTreeWidgetItem, QLabel, QPushButton, QMessageBox,
    QLineEdit, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from dal.competency_dal import CompetencyDAL
from dal.indicator_dal import IndicatorDAL
from dal.observable_behavior_dal import ObservableBehaviorDAL


class CompetencyTreeWidget(QWidget):
    """
    ویجت درخت شایستگی با ساختار سه‌لایه
    
    ویژگی‌ها:
    - نمایش درختی شایستگی‌ها، شاخص‌ها و رفتارهای قابل مشاهده
    - قابلیت انتخاب هر سطح
    - بازگشت شناسه‌های انتخاب‌شده
    - جستجو در ساختار
    """
    
    # سیگنال‌ها برای اطلاع از انتخاب
    competency_selected = Signal(int)      # شناسه شایستگی
    indicator_selected = Signal(int)       # شناسه شاخص
    behavior_selected = Signal(int)        # شناسه رفتار قابل مشاهده
    full_path_selected = Signal(dict)      # مسیر کامل انتخاب‌شده
    
    def __init__(self, parent=None, show_select_buttons=True):
        super().__init__(parent)
        
        self.competency_dal = CompetencyDAL()
        self.indicator_dal = IndicatorDAL()
        self.behavior_dal = ObservableBehaviorDAL()
        
        self.selected_competency_id = None
        self.selected_indicator_id = None
        self.selected_behavior_id = None
        
        self.show_select_buttons = show_select_buttons
        self.all_competencies = []
        
        self.setup_ui()
        self.load_competencies()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.setLayout(layout)
        
        # ===== هدر =====
        header_layout = QHBoxLayout()
        
        title_label = QLabel("📊 ساختار شایستگی‌ها")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #F4C542;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # دکمه جستجو
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 جستجو...")
        self.search_input.setStyleSheet("""
            QLineEdit {
    color: #F4C542;
    background-color: #08223A;
                padding: 4px 10px;
                border: 1px solid #8BC34A;
                border-radius: 4px;
                font-size: 12px;
                min-width: 150px;
            }
            QLineEdit:focus {
    color: #FFE8A3;
    background-color: #0B2E4F;
                border: 2px solid #F4C542;
            }
        """)
        self.search_input.textChanged.connect(self.search_competencies)
        header_layout.addWidget(self.search_input)
        
        layout.addLayout(header_layout)
        
        # ===== درخت =====
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["شایستگی / شاخص / رفتار", "شناسه"])
        self.tree.setColumnWidth(0, 350)
        self.tree.setColumnWidth(1, 60)
        self.tree.setStyleSheet("""
            QTreeWidget {
    color: #F4C542;
    gridline-color: #D9C36A;
                background-color: #0B2E4F;
                border: 1px solid #D9C36A;
                border-radius: 5px;
                padding: 5px;
                min-height: 200px;
            }
            QTreeWidget::item {
    color: #F4C542;
    border-bottom: 1px solid #D9C36A;
    background-color: #0B2E4F;
                padding: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #66BB6A;
                color: #F4C542;
            }
            QTreeWidget::item:hover {
    color: #FFE8A3;
                background-color: #174F78;
            }
            QTreeWidget::branch {
                background-color: transparent;
            }
        """)
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.tree)
        
        # ===== دکمه‌های انتخاب (اختیاری) =====
        if self.show_select_buttons:
            btn_layout = QHBoxLayout()
            btn_layout.setSpacing(8)
            
            self.select_btn = QPushButton("✅ انتخاب")
            self.select_btn.setStyleSheet("""
                QPushButton {
                    background-color: #66BB6A;
                    color: #F4C542;
                    padding: 6px 20px;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #8BC34A;
                }
            """)
            self.select_btn.clicked.connect(self.emit_selection)
            btn_layout.addWidget(self.select_btn)
            
            self.clear_btn = QPushButton("🗑️ پاک کردن انتخاب")
            self.clear_btn.setStyleSheet("""
                QPushButton {
                    background-color: #C62828;
                    color: #F4C542;
                    padding: 6px 20px;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #D94B4B;
                }
            """)
            self.clear_btn.clicked.connect(self.clear_selection)
            btn_layout.addWidget(self.clear_btn)
            
            btn_layout.addStretch()
            layout.addLayout(btn_layout)
        
        # ===== اطلاعات انتخاب =====
        self.info_label = QLabel("هیچ آیتمی انتخاب نشده است")
        self.info_label.setStyleSheet("""
            QLabel {
                color: #D9C36A;
                font-size: 12px;
                padding: 4px 8px;
                background-color: #0B2E4F;
                border-radius: 4px;
                border: 1px solid #08223A;
            }
        """)
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
    
    def load_competencies(self, search_term=None):
        """بارگذاری شایستگی‌ها در درخت"""
        try:
            # دریافت شایستگی‌ها با ساختار کامل
            if search_term:
                competencies = self.competency_dal.search(search_term)
            else:
                competencies = self.competency_dal.get_all(load_full=True)
            
            self.all_competencies = competencies
            
            self.tree.clear()
            
            if not competencies:
                empty_item = QTreeWidgetItem(self.tree)
                empty_item.setText(0, "⚠️ هیچ شایستگی‌ای یافت نشد")
                empty_item.setForeground(0, QColor(149, 165, 166))
                return
            
            # گروه‌بندی بر اساس دسته
            categories = {}
            for comp in competencies:
                category = comp.category or "other"
                if category not in categories:
                    categories[category] = []
                categories[category].append(comp)
            
            category_map = {
                "emotional": "عاطفی-هیجانی",
                "social": "اجتماعی",
                "educational": "آموزشی",
                "moral": "اخلاقی",
                "self_management": "خودمدیریتی",
                "participation": "مشارکت",
                "other": "سایر"
            }
            
            for category, comps in categories.items():
                cat_display = category_map.get(category, category)
                category_item = QTreeWidgetItem(self.tree)
                category_item.setText(0, f"📁 {cat_display}")
                category_item.setData(0, Qt.ItemDataRole.UserRole, "category")
                category_item.setExpanded(True)
                
                for comp in comps:
                    comp_item = QTreeWidgetItem(category_item)
                    comp_item.setText(0, f"📌 {comp.title}")
                    comp_item.setData(0, Qt.ItemDataRole.UserRole, "competency")
                    comp_item.setData(1, Qt.ItemDataRole.UserRole, comp.id)
                    
                    # نمایش شاخص‌ها
                    if comp.indicators:
                        for indicator in comp.indicators:
                            ind_item = QTreeWidgetItem(comp_item)
                            ind_item.setText(0, f"  🔹 {indicator.title}")
                            ind_item.setData(0, Qt.ItemDataRole.UserRole, "indicator")
                            ind_item.setData(1, Qt.ItemDataRole.UserRole, indicator.id)
                            ind_item.setData(2, Qt.ItemDataRole.UserRole, comp.id)
                            
                            # نمایش رفتارهای قابل مشاهده
                            behaviors = [b for b in comp.observable_behaviors 
                                       if b.indicator_id == indicator.id]
                            if behaviors:
                                for behavior in behaviors:
                                    beh_item = QTreeWidgetItem(ind_item)
                                    beh_item.setText(0, f"    • {behavior.text}")
                                    beh_item.setData(0, Qt.ItemDataRole.UserRole, "behavior")
                                    beh_item.setData(1, Qt.ItemDataRole.UserRole, behavior.id)
                                    beh_item.setData(2, Qt.ItemDataRole.UserRole, indicator.id)
                                    beh_item.setData(3, Qt.ItemDataRole.UserRole, comp.id)
                    
                    # اگر شاخص وجود ندارد
                    else:
                        no_ind_item = QTreeWidgetItem(comp_item)
                        no_ind_item.setText(0, "  ⚪ بدون شاخص")
                        no_ind_item.setForeground(0, QColor(149, 165, 166))
                    
                    # برای نمایش شایستگی بدون شاخص
                    if not comp.indicators:
                        comp_item.setExpanded(False)
            
            print(f"✅ {len(competencies)} شایستگی در درخت بارگذاری شد")
            
        except Exception as e:
            print(f"❌ خطا در بارگذاری شایستگی‌ها: {e}")
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری:\n{str(e)}")
    
    def search_competencies(self):
        """جستجو در شایستگی‌ها"""
        search_term = self.search_input.text().strip()
        self.load_competencies(search_term if search_term else None)
    
    def on_item_clicked(self, item, column):
        """وقتی روی آیتم کلیک می‌شود"""
        item_type = item.data(0, Qt.ItemDataRole.UserRole)
        
        if item_type == "competency":
            self.selected_competency_id = item.data(1, Qt.ItemDataRole.UserRole)
            self.selected_indicator_id = None
            self.selected_behavior_id = None
            
            comp_name = item.text(0).replace("📌 ", "")
            self.info_label.setText(f"✅ انتخاب شده: {comp_name} (شایستگی)")
            self.info_label.setStyleSheet("""
                QLabel {
                    color: #66BB6A;
                    font-size: 12px;
                    padding: 4px 8px;
                    background-color: #eafaf1;
                    border-radius: 4px;
                    border: 1px solid #a9dfbf;
                    font-weight: bold;
                }
            """)
            self.competency_selected.emit(self.selected_competency_id)
            self.full_path_selected.emit({
                'competency_id': self.selected_competency_id,
                'indicator_id': None,
                'behavior_id': None,
                'competency_name': comp_name,
                'indicator_name': None,
                'behavior_text': None
            })
            
        elif item_type == "indicator":
            self.selected_indicator_id = item.data(1, Qt.ItemDataRole.UserRole)
            self.selected_competency_id = item.data(2, Qt.ItemDataRole.UserRole)
            self.selected_behavior_id = None
            
            ind_name = item.text(0).replace("  🔹 ", "")
            self.info_label.setText(f"✅ انتخاب شده: {ind_name} (شاخص)")
            self.info_label.setStyleSheet("""
                QLabel {
                    color: #08223A;
                    font-size: 12px;
                    padding: 4px 8px;
                    background-color: #174F78;
                    border-radius: 4px;
                    border: 1px solid #D9C36A;
                    font-weight: bold;
                }
            """)
            self.indicator_selected.emit(self.selected_indicator_id)
            self.full_path_selected.emit({
                'competency_id': self.selected_competency_id,
                'indicator_id': self.selected_indicator_id,
                'behavior_id': None,
                'competency_name': None,
                'indicator_name': ind_name,
                'behavior_text': None
            })
            
        elif item_type == "behavior":
            self.selected_behavior_id = item.data(1, Qt.ItemDataRole.UserRole)
            self.selected_indicator_id = item.data(2, Qt.ItemDataRole.UserRole)
            self.selected_competency_id = item.data(3, Qt.ItemDataRole.UserRole)
            
            beh_text = item.text(0).replace("    • ", "")
            self.info_label.setText(f"✅ انتخاب شده: {beh_text} (رفتار قابل مشاهده)")
            self.info_label.setStyleSheet("""
                QLabel {
                    color: #66BB6A;
                    font-size: 12px;
                    padding: 4px 8px;
                    background-color: #66BB6A;
                    border-radius: 4px;
                    border: 1px solid #8BC34A;
                    font-weight: bold;
                }
            """)
            self.behavior_selected.emit(self.selected_behavior_id)
            self.full_path_selected.emit({
                'competency_id': self.selected_competency_id,
                'indicator_id': self.selected_indicator_id,
                'behavior_id': self.selected_behavior_id,
                'competency_name': None,
                'indicator_name': None,
                'behavior_text': beh_text
            })
    
    def on_item_double_clicked(self, item, column):
        """وقتی روی آیتم دابل کلیک می‌شود"""
        self.on_item_clicked(item, column)
        self.emit_selection()
    
    def emit_selection(self):
        """ارسال سیگنال انتخاب"""
        if self.selected_behavior_id:
            self.behavior_selected.emit(self.selected_behavior_id)
        elif self.selected_indicator_id:
            self.indicator_selected.emit(self.selected_indicator_id)
        elif self.selected_competency_id:
            self.competency_selected.emit(self.selected_competency_id)
        else:
            QMessageBox.warning(self, "توجه", "لطفاً یک آیتم را انتخاب کنید.")
    
    def clear_selection(self):
        """پاک کردن انتخاب"""
        self.selected_competency_id = None
        self.selected_indicator_id = None
        self.selected_behavior_id = None
        
        self.info_label.setText("هیچ آیتمی انتخاب نشده است")
        self.info_label.setStyleSheet("""
            QLabel {
                color: #D9C36A;
                font-size: 12px;
                padding: 4px 8px;
                background-color: #0B2E4F;
                border-radius: 4px;
                border: 1px solid #08223A;
            }
        """)
        
        # لغو انتخاب در درخت
        self.tree.clearSelection()
    
    def get_selected_ids(self):
        """
        دریافت شناسه‌های انتخاب‌شده
        
        Returns:
            dict: {
                'competency_id': int or None,
                'indicator_id': int or None,
                'behavior_id': int or None
            }
        """
        return {
            'competency_id': self.selected_competency_id,
            'indicator_id': self.selected_indicator_id,
            'behavior_id': self.selected_behavior_id
        }
    
    def get_selected_names(self):
        """
        دریافت نام‌های انتخاب‌شده
        
        Returns:
            dict: {
                'competency_name': str,
                'indicator_name': str,
                'behavior_text': str
            }
        """
        result = {
            'competency_name': None,
            'indicator_name': None,
            'behavior_text': None
        }
        
        # پیدا کردن آیتم انتخاب‌شده
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            category = root.child(i)
            for j in range(category.childCount()):
                comp = category.child(j)
                comp_id = comp.data(1, Qt.ItemDataRole.UserRole)
                if comp_id == self.selected_competency_id:
                    result['competency_name'] = comp.text(0).replace("📌 ", "")
                
                for k in range(comp.childCount()):
                    ind = comp.child(k)
                    if ind.data(1, Qt.ItemDataRole.UserRole) == self.selected_indicator_id:
                        result['indicator_name'] = ind.text(0).replace("  🔹 ", "")
                    
                    for l in range(ind.childCount()):
                        beh = ind.child(l)
                        if beh.data(1, Qt.ItemDataRole.UserRole) == self.selected_behavior_id:
                            result['behavior_text'] = beh.text(0).replace("    • ", "")
        
        return result
    
    def get_selected_full_path(self):
        """
        دریافت مسیر کامل انتخاب‌شده
        
        Returns:
            dict: {
                'competency_id': int,
                'indicator_id': int or None,
                'behavior_id': int or None,
                'full_path': str
            }
        """
        ids = self.get_selected_ids()
        names = self.get_selected_names()
        
        path_parts = []
        if names['competency_name']:
            path_parts.append(names['competency_name'])
        if names['indicator_name']:
            path_parts.append(names['indicator_name'])
        if names['behavior_text']:
            path_parts.append(names['behavior_text'])
        
        return {
            'competency_id': ids['competency_id'],
            'indicator_id': ids['indicator_id'],
            'behavior_id': ids['behavior_id'],
            'full_path': " → ".join(path_parts) if path_parts else "ثبت نشده",
            'competency_name': names['competency_name'],
            'indicator_name': names['indicator_name'],
            'behavior_text': names['behavior_text']
        }
    
    def set_selection_by_ids(self, competency_id=None, indicator_id=None, behavior_id=None):
        """
        تنظیم انتخاب بر اساس شناسه‌ها
        
        Args:
            competency_id: شناسه شایستگی
            indicator_id: شناسه شاخص
            behavior_id: شناسه رفتار قابل مشاهده
        """
        self.selected_competency_id = competency_id
        self.selected_indicator_id = indicator_id
        self.selected_behavior_id = behavior_id
        
        # پیدا کردن آیتم‌ها در درخت
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            category = root.child(i)
            for j in range(category.childCount()):
                comp = category.child(j)
                comp_id = comp.data(1, Qt.ItemDataRole.UserRole)
                
                if comp_id == competency_id:
                    comp.setSelected(True)
                    self.tree.scrollToItem(comp)
                    
                    if indicator_id:
                        for k in range(comp.childCount()):
                            ind = comp.child(k)
                            if ind.data(1, Qt.ItemDataRole.UserRole) == indicator_id:
                                ind.setSelected(True)
                                self.tree.scrollToItem(ind)
                                
                                if behavior_id:
                                    for l in range(ind.childCount()):
                                        beh = ind.child(l)
                                        if beh.data(1, Qt.ItemDataRole.UserRole) == behavior_id:
                                            beh.setSelected(True)
                                            self.tree.scrollToItem(beh)
                                            break
                                break
                    break
        
        # به‌روزرسانی اطلاعات
        if behavior_id:
            self.info_label.setText(f"✅ انتخاب شد: رفتار قابل مشاهده (ID: {behavior_id})")
        elif indicator_id:
            self.info_label.setText(f"✅ انتخاب شد: شاخص (ID: {indicator_id})")
        elif competency_id:
            self.info_label.setText(f"✅ انتخاب شد: شایستگی (ID: {competency_id})")
        
        self.info_label.setStyleSheet("""
            QLabel {
                color: #66BB6A;
                font-size: 12px;
                padding: 4px 8px;
                background-color: #eafaf1;
                border-radius: 4px;
                border: 1px solid #a9dfbf;
                font-weight: bold;
            }
        """)
    
    def refresh(self):
        """به‌روزرسانی درخت"""
        self.load_competencies()