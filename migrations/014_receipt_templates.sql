-- Admin-selectable receipt design. Existing pharmacies keep a safe 80mm default.
INSERT OR IGNORE INTO Pharmacy_Settings (setting_key, setting_value)
VALUES ('receipt_template', 'standard_80');
