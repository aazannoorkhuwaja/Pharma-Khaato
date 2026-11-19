"""Expose visible form labels as accessible names and keyboard buddies."""
from PySide6.QtWidgets import QFormLayout, QLabel, QWidget
from PySide6.QtCore import Qt


def label_form_controls(root):
    for form in root.findChildren(QFormLayout):
        for row in range(form.rowCount()):
            label_item = form.itemAt(row, QFormLayout.LabelRole)
            field_item = form.itemAt(row, QFormLayout.FieldRole)
            if not label_item or not field_item:
                continue
            label, field = label_item.widget(), field_item.widget()
            if not isinstance(label, QLabel) or field is None:
                continue
            control = field
            if control.focusPolicy() == Qt.NoFocus:
                control = next((child for child in field.findChildren(QWidget)
                                if child.focusPolicy() != Qt.NoFocus), None)
            if control is None:
                continue
            if not control.accessibleName():
                control.setAccessibleName(label.text().replace('&', '').rstrip(':').strip())
            label.setBuddy(control)
