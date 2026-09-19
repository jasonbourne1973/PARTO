"""
ویجت نمایش پیشنهادات هوشمند - نمایش در پرونده دانش‌آموز
"""

import os
import sys

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.recommendation import Recommendation
from services.intervention_suggester import InterventionSuggester
from services.recommendation_service import RecommendationService
from utils.logger import get_logger


class RecommendationWidget(QWidget):
    """
    ویجت نمایش پیشنهادات هوشمند
    
    ویژگی‌ها:
    - نمایش پیشنهادات تولیدشده
    - نمایش وضعیت هر پیشنهاد
    - امکان پذیرش/رد/اجرا/تکمیل پیشنهاد
    - نمایش اولویت و دسته‌بندی
    """
    
    recommendation_updated = Signal()
    intervention_requested = Signal(dict)  # برای درخواست ثبت مداخله
    
    def __init__(self, profile_id=None, parent=None):
        super().__init__(parent)
        
        self.profile_id = profile_id
        self.recommendation_service = RecommendationService()
        self.intervention_suggester = InterventionSuggester()
        self.logger = get_logger(self.__class__.__name__)
        
        self.recommendations = []
        self.current_recommendation = None
        
        self.setup_ui()
        
        if self.profile_id:
            self.load_recommendations()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)
        self.setLayout(main_layout)
        
        # ===== هدر =====
        header_layout = QHBoxLayout()
        
        title_label = QLabel("💡 پیشنهادات هوشمند")
        title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #F4C542;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # دکمه تولید پیشنهادات جدید
        self.generate_btn = QPushButton("🔄 تولید پیشنهادات جدید")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #0B2E4F;
                border: none;
                border-radius: 6px;
                padding: 4px 14px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #08223A;
            }
        """)
        self.generate_btn.clicked.connect(self.generate_recommendations)
        header_layout.addWidget(self.generate_btn)
        
        main_layout.addLayout(header_layout)
        
        # ===== اسکرول برای لیست پیشنهادات =====
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #08223A;
                width: 4px;
                border-radius: 2px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background-color: #D9C36A;
                border-radius: 2px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #D9C36A;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(8)
        
        # پیام خالی
        self.empty_label = QLabel("✅ هیچ پیشنهاد فعالی وجود ندارد.\nبرای دریافت پیشنهادات جدید، روی دکمه 'تولید پیشنهادات جدید' کلیک کنید.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("""
            QLabel {
                color: #D9C36A;
                font-size: 13px;
                padding: 30px 20px;
                background-color: #0B2E4F;
                border-radius: 8px;
                border: 1px dashed #D9C36A;
            }
        """)
        self.container_layout.addWidget(self.empty_label)
        
        scroll.setWidget(self.container)
        main_layout.addWidget(scroll)
        
        # ===== خلاصه آماری =====
        self.summary_frame = QFrame()
        self.summary_frame.setStyleSheet("""
            QFrame {
                background-color: #0B2E4F;
                border-radius: 8px;
                border: 1px solid #D9C36A;
            }
        """)
        summary_layout = QHBoxLayout(self.summary_frame)
        summary_layout.setContentsMargins(12, 8, 12, 8)
        summary_layout.setSpacing(20)
        
        self.summary_labels = {}
        statuses = [
            ('total', '📊 کل', '#F4C542'),
            ('pending', '⏳ در انتظار', '#F59E0B'),
            ('accepted', '✅ پذیرفته شده', '#22C55E'),
            ('implemented', '🔄 اجرا شده', '#174F78'),
            ('completed', '✔️ تکمیل شده', '#66BB6A')
        ]
        
        for key, label, color in statuses:
            lbl = QLabel(f"{label}: 0")
            lbl.setStyleSheet(f"font-size: 11px; color: {color}; font-weight: 600;")
            summary_layout.addWidget(lbl)
            self.summary_labels[key] = lbl
        
        summary_layout.addStretch()
        main_layout.addWidget(self.summary_frame)
        
        # مخفی کردن در ابتدا
        self.summary_frame.hide()
    
    def set_profile_id(self, profile_id):
        """تنظیم شناسه پرونده دانش‌آموز"""
        self.profile_id = profile_id
        self.load_recommendations()
    
    def load_recommendations(self):
        """بارگذاری پیشنهادات"""
        if not self.profile_id:
            self.clear_display()
            return
        
        try:
            # دریافت پیشنهادات فعال
            self.recommendations = self.recommendation_service.get_active_recommendations(
                self.profile_id
            )
            
            # اگر پیشنهاد فعالی وجود نداشت، همه پیشنهادات را بگیر
            if not self.recommendations:
                self.recommendations = self.recommendation_service.get_recommendations_for_student(
                    self.profile_id
                )
            
            self.display_recommendations()
            self.update_summary()
            
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری پیشنهادات: {e}")
            QMessageBox.warning(self, "خطا", f"مشکل در بارگذاری پیشنهادات:\n{str(e)}")
    
    def display_recommendations(self):
        """نمایش پیشنهادات در ویجت"""
        # پاک کردن لیست قبلی
        for i in reversed(range(self.container_layout.count())):
            widget = self.container_layout.itemAt(i).widget()
            if widget and widget != self.empty_label:
                widget.deleteLater()
        
        # مخفی کردن پیام خالی
        self.empty_label.hide()
        
        if not self.recommendations:
            self.empty_label.show()
            self.summary_frame.hide()
            return
        
        # نمایش پیشنهادات
        for rec in self.recommendations:
            item = self._create_recommendation_item(rec)
            self.container_layout.addWidget(item)
        
        self.summary_frame.show()
    
    def _create_recommendation_item(self, recommendation):
        """ایجاد آیتم نمایش یک پیشنهاد"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #0B2E4F;
                border: 1px solid #D9C36A;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        # ===== ردیف اول: عنوان و وضعیت =====
        top_row = QHBoxLayout()
        
        # عنوان
        title_label = QLabel(recommendation.title)
        title_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #F4C542;")
        title_label.setWordWrap(True)
        top_row.addWidget(title_label, 2)
        
        # برچسب اولویت
        priority_label = QLabel(recommendation.priority_display)
        priority_label.setStyleSheet(f"""
            QLabel {{
                font-size: 10px;
                font-weight: bold;
                color: #0B2E4F;
                background-color: {recommendation.priority_color};
                padding: 2px 10px;
                border-radius: 10px;
            }}
        """)
        top_row.addWidget(priority_label)
        
        # برچسب وضعیت
        status_label = QLabel(recommendation.status_display)
        status_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                font-weight: bold;
                background-color: #08223A;
                padding: 2px 10px;
                border-radius: 10px;
                color: #475569;
            }
        """)
        top_row.addWidget(status_label)
        
        layout.addLayout(top_row)
        
        # ===== ردیف دوم: دسته‌بندی و امتیاز =====
        middle_row = QHBoxLayout()
        
        category_label = QLabel(f"📂 {recommendation.category_display}")
        category_label.setStyleSheet("font-size: 11px; color: #D9C36A;")
        middle_row.addWidget(category_label)
        
        middle_row.addStretch()
        
        score_label = QLabel(f"⭐ امتیاز: {recommendation.score}")
        score_label.setStyleSheet("font-size: 11px; color: #F59E0B; font-weight: 600;")
        middle_row.addWidget(score_label)
        
        layout.addLayout(middle_row)
        
        # ===== توضیحات =====
        desc_label = QLabel(recommendation.description)
        desc_label.setStyleSheet("font-size: 12px; color: #475569;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # ===== اقدام پیشنهادی =====
        if recommendation.suggested_action:
            action_label = QLabel(f"📌 اقدام پیشنهادی: {recommendation.suggested_action}")
            action_label.setStyleSheet("""
                font-size: 12px;
                color: #0B2E4F;
                background-color: #0B2E4F;
                padding: 4px 8px;
                border-radius: 4px;
            """)
            action_label.setWordWrap(True)
            layout.addWidget(action_label)
        
        # ===== دکمه‌های عملیات =====
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        
        if recommendation.is_pending:
            accept_btn = QPushButton("✅ پذیرش")
            accept_btn.setStyleSheet("""
                QPushButton {
                    background-color: #22C55E;
                    color: #0B2E4F;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #16A34A;
                }
            """)
            accept_btn.clicked.connect(lambda: self.accept_recommendation(recommendation))
            btn_row.addWidget(accept_btn)
            
            reject_btn = QPushButton("❌ رد")
            reject_btn.setStyleSheet("""
                QPushButton {
                    background-color: #EF4444;
                    color: #0B2E4F;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #DC2626;
                }
            """)
            reject_btn.clicked.connect(lambda: self.reject_recommendation(recommendation))
            btn_row.addWidget(reject_btn)
        
        elif recommendation.status == Recommendation.STATUS_ACCEPTED:
            implement_btn = QPushButton("🚀 اجرا")
            implement_btn.setStyleSheet("""
                QPushButton {
                    background-color: #174F78;
                    color: #0B2E4F;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #0B2E4F;
                }
            """)
            implement_btn.clicked.connect(lambda: self.implement_recommendation(recommendation))
            btn_row.addWidget(implement_btn)
        
        elif recommendation.status == Recommendation.STATUS_IMPLEMENTED:
            complete_btn = QPushButton("✔️ تکمیل")
            complete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #66BB6A;
                    color: #0B2E4F;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #7C3AED;
                }
            """)
            complete_btn.clicked.connect(lambda: self.complete_recommendation(recommendation))
            btn_row.addWidget(complete_btn)
        
        # دکمه ثبت مداخله (اگر پیشنهاد مداخله باشد)
        if recommendation.category == 'intervention' and recommendation.suggested_intervention_type:
            intervention_btn = QPushButton("🛠️ ثبت مداخله")
            intervention_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F59E0B;
                    color: #0B2E4F;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #D97706;
                }
            """)
            intervention_btn.clicked.connect(lambda: self.request_intervention(recommendation))
            btn_row.addWidget(intervention_btn)
        
        btn_row.addStretch()
        layout.addLayout(btn_row)
        
        # ذخیره مرجع به پیشنهاد
        card.recommendation = recommendation
        
        return card
    
    def generate_recommendations(self):
        """تولید پیشنهادات جدید"""
        if not self.profile_id:
            QMessageBox.warning(self, "توجه", "لطفاً ابتدا یک دانش‌آموز را انتخاب کنید.")
            return
        
        reply = QMessageBox.question(
            self,
            "تولید پیشنهادات جدید",
            "آیا از تولید پیشنهادات جدید برای این دانش‌آموز اطمینان دارید؟\nپیشنهادات قبلی حذف نمی‌شوند.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        try:
            recommendations = self.recommendation_service.generate_recommendations(
                self.profile_id
            )
            
            if recommendations:
                QMessageBox.information(
                    self,
                    "موفقیت",
                    f"{len(recommendations)} پیشنهاد جدید برای این دانش‌آموز تولید شد."
                )
                self.load_recommendations()
            else:
                QMessageBox.information(
                    self,
                    "توجه",
                    "هیچ پیشنهاد جدیدی برای این دانش‌آموز تولید نشد."
                )
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در تولید پیشنهادات:\n{str(e)}")
    
    def accept_recommendation(self, recommendation):
        """پذیرش پیشنهاد"""
        try:
            self.recommendation_service.accept_recommendation(recommendation.id)
            QMessageBox.information(self, "موفقیت", "پیشنهاد با موفقیت پذیرفته شد.")
            self.load_recommendations()
            self.recommendation_updated.emit()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در پذیرش:\n{str(e)}")
    
    def reject_recommendation(self, recommendation):
        """رد پیشنهاد"""
        notes, ok = QMessageBox.getText(
            self,
            "رد پیشنهاد",
            "لطفاً دلیل رد پیشنهاد را وارد کنید (اختیاری):",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        
        if not ok:
            return
        
        try:
            self.recommendation_service.reject_recommendation(recommendation.id, notes)
            QMessageBox.information(self, "موفقیت", "پیشنهاد با موفقیت رد شد.")
            self.load_recommendations()
            self.recommendation_updated.emit()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در رد:\n{str(e)}")
    
    def implement_recommendation(self, recommendation):
        """اجرای پیشنهاد"""
        try:
            self.recommendation_service.implement_recommendation(recommendation.id)
            QMessageBox.information(self, "موفقیت", "پیشنهاد با موفقیت اجرا شد.")
            self.load_recommendations()
            self.recommendation_updated.emit()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در اجرا:\n{str(e)}")
    
    def complete_recommendation(self, recommendation):
        """تکمیل پیشنهاد"""
        feedback, ok = QMessageBox.getText(
            self,
            "تکمیل پیشنهاد",
            "لطفاً بازخورد خود را وارد کنید (اختیاری):",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        
        if not ok:
            return
        
        try:
            self.recommendation_service.complete_recommendation(recommendation.id, feedback)
            QMessageBox.information(self, "موفقیت", "پیشنهاد با موفقیت تکمیل شد.")
            self.load_recommendations()
            self.recommendation_updated.emit()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در تکمیل:\n{str(e)}")
    
    def request_intervention(self, recommendation):
        """درخواست ثبت مداخله"""
        data = {
            'recommendation_id': recommendation.id,
            'suggested_type': recommendation.suggested_intervention_type,
            'competency_id': recommendation.related_competency_id,
            'title': recommendation.title
        }
        self.intervention_requested.emit(data)
    
    def update_summary(self):
        """به‌روزرسانی خلاصه آماری"""
        try:
            summary = self.recommendation_service.get_recommendation_summary(self.profile_id)
            
            self.summary_labels['total'].setText(f"📊 کل: {summary.get('total', 0)}")
            self.summary_labels['pending'].setText(f"⏳ در انتظار: {summary.get('pending', 0)}")
            self.summary_labels['accepted'].setText(f"✅ پذیرفته شده: {summary.get('accepted', 0)}")
            self.summary_labels['implemented'].setText(f"🔄 اجرا شده: {summary.get('implemented', 0)}")
            self.summary_labels['completed'].setText(f"✔️ تکمیل شده: {summary.get('completed', 0)}")
            
        except Exception as e:
            self.logger.error(f"خطا در به‌روزرسانی خلاصه: {e}")
    
    def clear_display(self):
        """پاک کردن نمایش"""
        for i in reversed(range(self.container_layout.count())):
            widget = self.container_layout.itemAt(i).widget()
            if widget and widget != self.empty_label:
                widget.deleteLater()
        
        self.empty_label.show()
        self.summary_frame.hide()