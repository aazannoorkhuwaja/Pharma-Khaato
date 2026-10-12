"""
TaxSettingsWidget — unmistakable GST configuration with Pakistan regulatory
presets (0% life-saving/exempt drugs vs 18% standard GST).

Drop-in widget: add to settings_screen layout. Persists through
SettingsService under the key 'default_tax_rate' as a percentage string,
matching the existing normalisation in SettingsService.get_tax_rate().
File: ui/widgets/tax_settings.py
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QDoubleSpinBox, QRadioButton, QButtonGroup, QFrame,
)

from controllers.settings_controller import SettingsController

_SETTINGS_CONTROLLER = SettingsController()


class TaxSettingsWidget(QWidget):
    """Radio-preset tax rate editor with explicit regulatory labeling."""

    PRESET_EXEMPT = 0.0
    PRESET_STANDARD = 18.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._building = True
        self._init_ui()
        self._load_current()
        self._building = False

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        title = QLabel("Sales Tax")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)

        note = QLabel(
            "Choose the default tax rate used for new sales. "
            "Confirm the correct rate for your pharmacy before saving."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        frame = QFrame(self)
        frame.setObjectName("taxCard")
        inner = QVBoxLayout(frame)
        inner.setSpacing(8)

        self.btn_group = QButtonGroup(self)
        self.rb_exempt = QRadioButton("0% — No tax", self)
        self.rb_standard = QRadioButton("18% — Standard rate", self)
        self.rb_custom = QRadioButton("Custom rate:", self)
        for rb in (self.rb_exempt, self.rb_standard, self.rb_custom):
            self.btn_group.addButton(rb)
            inner.addWidget(rb)

        custom_row = QHBoxLayout()
        custom_row.addSpacing(24)
        self.tax_spinbox = QDoubleSpinBox(self)
        self.tax_spinbox.setRange(0.00, 100.00)
        self.tax_spinbox.setDecimals(2)
        self.tax_spinbox.setSingleStep(0.5)
        self.tax_spinbox.setSuffix(" %")
        custom_row.addWidget(self.tax_spinbox)
        custom_row.addStretch(1)
        inner.addLayout(custom_row)

        layout.addWidget(frame)

        # Live preview so the cashier sees the effect before saving
        self.preview = QLabel(self)
        self.preview.setStyleSheet("color: gray;")
        layout.addWidget(self.preview)

        self.tax_spinbox.valueChanged.connect(self._on_custom_changed)
        self.btn_group.buttonToggled.connect(lambda *_: self._update_preview())
        self._update_preview()

    def _current_rate_pct(self) -> float:
        raw = _SETTINGS_CONTROLLER.get("default_tax_rate", "0.0")
        try:
            val = float(raw)
        except (TypeError, ValueError):
            return 0.0
        return val if val <= 1.0 else val  # get_setting stores percentage form

    def _load_current(self):
        pct = self._current_rate_pct()
        if abs(pct - self.PRESET_EXEMPT) < 1e-9:
            self.rb_exempt.setChecked(True)
        elif abs(pct - self.PRESET_STANDARD) < 1e-9:
            self.rb_standard.setChecked(True)
        else:
            self.rb_custom.setChecked(True)
            self.tax_spinbox.setValue(pct)

    def _on_custom_changed(self, value: float):
        if not self._building:
            self.rb_custom.setChecked(True)
        self._update_preview()

    def _active_pct(self) -> float:
        if self.rb_exempt.isChecked():
            return self.PRESET_EXEMPT
        if self.rb_standard.isChecked():
            return self.PRESET_STANDARD
        return self.tax_spinbox.value()

    def _update_preview(self):
        pct = self._active_pct()
        self.preview.setText(f"Tax on new sales: {pct:.2f}%")

    def save(self) -> bool:
        """Persist the selected rate as a percentage string."""
        return bool(_SETTINGS_CONTROLLER.set("default_tax_rate", f"{self._active_pct():.2f}"))
